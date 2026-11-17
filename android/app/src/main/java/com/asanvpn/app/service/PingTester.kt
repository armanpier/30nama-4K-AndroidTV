package com.asanvpn.app.service

import android.content.Context
import android.util.Log
import com.asanvpn.app.data.models.VpnNode
import com.asanvpn.app.service.v2ray.V2RayConfigBuilder
import com.asanvpn.app.service.v2ray.V2RayCoreManager
import com.asanvpn.app.util.AppLogger
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import libv2ray.Libv2ray
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.InetSocketAddress
import java.net.Socket
import java.util.Collections
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

object PingTester {

    private const val TAG = "PingTester"
    private const val TEST_URL_PRIMARY = "https://cp.cloudflare.com/generate_204"
    private const val TEST_URL_FALLBACK = "https://www.gstatic.com/generate_204"
    private const val SPEED_TEST_URL_PRIMARY = "https://speed.cloudflare.com/__down?bytes=4000000"
    private const val SPEED_TEST_URL_FALLBACK = "https://speedtest.tele2.net/4MB.zip"
    private const val GEMINI_TEST_URL = "https://gemini.google.com"
    private const val GEMINI_API_TEST_URL = "https://generativelanguage.googleapis.com"

    data class GeminiCheckResult(
        val isSuccess: Boolean,
        val latencyMs: Long,
        val message: String
    )

    /**
     * Connects IMMEDIATELY to the first verified working link (fast connect),
     * while continuing in the background to evaluate all candidates to switch
     * to the fastest one without keeping the user waiting.
     */
    /**
     * Priority-based Waterfall / Cascade Connect & Optimize:
     * 1. Groups candidate nodes strictly by panel priority (Priority 1 = highest, Priority 2 = next, etc.).
     * 2. Tests the highest-priority panel (Priority 1) first using REAL HTTP 204 tunnel delay.
     * 3. If ANY node in Priority 1 succeeds with a valid real delay (> 0):
     *    - Connects immediately to it (fast connect).
     *    - Optimizes within Priority 1 only.
     *    - HALTS the cascade completely (does NOT touch lower priority panels).
     * 4. If and ONLY if ALL nodes in Priority 1 fail/timeout (blocked/down):
     *    - Cascades to Priority 2, runs real delay testing on Priority 2 nodes.
     * 5. Repeats down the cascade for Priority 3, etc.
     */
    suspend fun connectFastAndOptimize(
        context: Context? = null,
        nodes: List<VpnNode>,
        isGeminiOptimizationEnabled: Boolean = false,
        onFirstOkNode: suspend (VpnNode) -> Unit,
        onFastestNodeFound: suspend (VpnNode) -> Unit
    ) = withContext(Dispatchers.IO) {
        if (nodes.isEmpty()) return@withContext
        context?.let {
            V2RayCoreManager.initCore(it)
            com.asanvpn.app.data.NodeMetricsCache.init(it)
        }

        if (nodes.size == 1) {
            val single = nodes[0]
            val delay = measureRealDelay(single, 5000L)
            if (delay > 0) {
                if (isGeminiOptimizationEnabled) {
                    val cached = com.asanvpn.app.data.NodeMetricsCache.getGeminiCompatibility(single)
                    val gDelay = if (cached != null) {
                        if (cached.first) {
                            val lat = if (cached.second > 0) cached.second else delay
                            AppLogger.logUser("⚡ سرور [${single.remark}] سازگار با Gemini تایید شد (${lat}ms - از کش)")
                            lat
                        } else {
                            AppLogger.logUser("⚠️ سرور [${single.remark}] فاقد دسترسی به Gemini (ثبت در کش)")
                            -1L
                        }
                    } else {
                        val d = measureGeminiDelay(single, 4000L)
                        com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(single, d > 0, d)
                        if (d > 0) {
                            AppLogger.logUser("✨ سرور [${single.remark}] سازگار با Gemini تایید شد (${d}ms)")
                        } else {
                            AppLogger.logUser("⚠️ سرور [${single.remark}] فاقد دسترسی کامل به Gemini است")
                        }
                        d
                    }
                    if (gDelay <= 0) return@withContext
                }
                single.latencyMs = delay
                onFirstOkNode(single)
                onFastestNodeFound(single)
            } else {
                AppLogger.logUser("⚠️ سرور [${single.remark}] پاسخ نداد.")
            }
            return@withContext
        }

        val usableNodes = nodes.filter { isUsableEgressNode(it) }
        val candidatePool = if (usableNodes.isNotEmpty()) usableNodes else nodes

        // Group candidate nodes strictly by panel priority (1 = highest, 2, 3...)
        val priorityTiers = candidatePool
            .groupBy { it.panelPriority ?: 1 }
            .toSortedMap()

        val firstConnected = AtomicBoolean(false)
        val bestLatency = java.util.concurrent.atomic.AtomicLong(Long.MAX_VALUE)
        var bestNode: VpnNode? = null

        // WATERFALL CASCADE LOOP:
        // Always test Priority 1 first with increased patience/timeout. Only cascade to Priority 2/3 if Priority 1 completely fails.
        for ((tier, tierNodes) in priorityTiers) {
            val tierName = tierNodes.firstOrNull()?.panelName ?: "پنل اولویت $tier"
            val isTopPriority = (tier == priorityTiers.firstKey())
            val tcpTimeout = if (isTopPriority) 2500 else 1200
            val realDelayTimeout = if (isTopPriority) 7000L else 3500L

            Log.i(TAG, "==> [Priority Cascade] Testing Priority Tier $tier ($tierName) with ${tierNodes.size} candidate nodes (timeout: ${realDelayTimeout}ms)...")
            AppLogger.logUser("🔍 بررسی سرورهای $tierName...")
            AppLogger.logAdmin("Testing Tier $tier ($tierName) with ${tierNodes.size} nodes")

            // Parallel TCP prescan for this tier to identify responsive endpoints
            val tcpResults = tierNodes.map { node ->
                async {
                    val tcp = testTcpLatency(node.server, node.port, tcpTimeout)
                    Pair(node, tcp)
                }
            }.awaitAll()

            val responsive = tcpResults.filter { it.second > 0 }.sortedBy { it.second }.map { it.first }
            val tierCandidatesToTest = if (responsive.isNotEmpty()) responsive.take(10) else tierNodes.take(10)

            val testSemaphore = Semaphore(2)
            // Test Real Delay via Libv2ray HTTP 204 on this tier's candidates with generous patience for top tier
            coroutineScope {
                tierCandidatesToTest.forEach { node ->
                    launch {
                        val realDelay = testSemaphore.withPermit {
                            measureRealDelay(node, realDelayTimeout)
                        }
                        node.latencyMs = realDelay
                        if (realDelay > 0) {
                            if (isGeminiOptimizationEnabled) {
                                val cached = com.asanvpn.app.data.NodeMetricsCache.getGeminiCompatibility(node)
                                val geminiDelay = if (cached != null) {
                                    if (cached.first) {
                                        val lat = if (cached.second > 0) cached.second else realDelay
                                        Log.i(TAG, "Tier $tier cached Gemini OK: [${node.remark}] (${lat}ms)")
                                        AppLogger.logUser("⚡ [${node.remark}] سازگار با Gemini (استفاده از کش: ${lat}ms)")
                                        lat
                                    } else {
                                        Log.i(TAG, "Tier $tier cached Gemini failed: [${node.remark}]")
                                        AppLogger.logUser("⚠️ [${node.remark}] فاقد دسترسی به Gemini (ثبت در کش - رد شد)")
                                        -1L
                                    }
                                } else {
                                    val measured = measureGeminiDelay(node, realDelayTimeout)
                                    if (measured <= 0) {
                                        com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(node, false, -1L)
                                        Log.w(TAG, "Tier $tier candidate [${node.remark}] failed Gemini test. Saved to cache.")
                                        AppLogger.logUser("⚠️ سرور [${node.remark}] فاقد دسترسی به Gemini (خطای تحریم گوگل)")
                                        -1L
                                    } else {
                                        com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(node, true, measured)
                                        Log.i(TAG, "Tier $tier candidate [${node.remark}] passed Gemini test (${measured}ms). Saved to cache.")
                                        AppLogger.logUser("✨ سرور [${node.remark}] سازگار با Gemini تایید شد (${measured}ms)")
                                        measured
                                    }
                                }

                                if (geminiDelay <= 0) {
                                    return@launch
                                }
                            }

                            Log.i(TAG, "Tier $tier Verified OK: [${node.remark}] -> REAL latency: ${realDelay}ms")
                            AppLogger.logLinkTest(node.remark, realDelay, isSuccess = true)

                            if (firstConnected.compareAndSet(false, true)) {
                                bestNode = node
                                bestLatency.set(realDelay)
                                Log.i(TAG, ">> [Cascade SUCCESS] Connecting immediately to Priority Tier $tier server [${node.remark}] (${realDelay}ms)")
                                AppLogger.logUser("🚀 انتخاب سرور پایدار [${node.remark}]")
                                AppLogger.logAdmin("Cascade SUCCESS. Assigned node [${node.remark}]")
                                onFirstOkNode(node)
                            } else if (realDelay < bestLatency.get() - 25L) {
                                val prevRemark = bestNode?.remark ?: "unknown"
                                val prevLat = bestLatency.get()
                                bestNode = node
                                bestLatency.set(realDelay)
                                Log.i(TAG, ">> [Cascade OPTIMIZE] Faster server found in Priority Tier $tier [${node.remark}] (${realDelay}ms vs $prevRemark ${prevLat}ms) -> Switching")
                                AppLogger.logUser("⚡ تعویض به سرور سریع‌تر: [${node.remark}] (${realDelay}ms)")
                                AppLogger.logAdmin("Cascade OPTIMIZE: [${node.remark}] (${realDelay}ms vs $prevRemark ${prevLat}ms)")
                                onFastestNodeFound(node)
                            }
                        } else {
                            Log.d(TAG, "Tier $tier candidate failed: [${node.remark}]")
                            AppLogger.logLinkTest(node.remark, -1L, isSuccess = false)
                        }
                    }
                }
            }

            // If ANY node in this priority tier succeeded, stop the cascade!
            if (firstConnected.get()) {
                Log.i(TAG, ">> [Cascade HALTED] Connected to working server in Priority Tier $tier ($tierName). Cascade complete.")
                AppLogger.logUser("✅ اتصال به سرورهای $tierName نهایی شد")
                AppLogger.logAdmin(">> [Cascade HALTED] Tier $tier successful.")
                return@withContext
            }

            Log.w(TAG, ">> [Cascade FAILOVER] All candidate nodes in Priority Tier $tier failed real delay test! Cascading to next priority tier...")
            AppLogger.logUser("⚠️ سرورهای $tierName پاسخ ندادند. در حال بررسی اولویت بعدی...")
            AppLogger.logAdmin(">> [Cascade FAILOVER] Tier $tier timed out. Cascading to next tier.")
        }

        // If ALL priority tiers failed real delay test, NEVER fake a connection! Keep disconnected.
        if (!firstConnected.get()) {
            Log.w(TAG, ">> [Cascade EXHAUSTED] All nodes across all tiers failed real delay test.")
            AppLogger.logUser("❌ هیچ سرور فعالی پاسخ نداد. لطفاً وضعیت اینترنت را بررسی نمایید.")
            AppLogger.logAdmin("Cascade EXHAUSTED. All candidate nodes timed out.")
        }
    }

    /**
     * Finds the fastest, verified working proxy using REALTIME HTTP roundtrip latency
     * through the V2Ray/Xray tunnel rather than a simple TCP handshake, adhering strictly
     * to panel waterfall priority.
     */
    suspend fun findFastestNode(context: Context? = null, nodes: List<VpnNode>): VpnNode = withContext(Dispatchers.IO) {
        if (nodes.isEmpty()) throw IllegalArgumentException("Node list is empty")
        if (nodes.size == 1) return@withContext nodes[0]

        context?.let { V2RayCoreManager.initCore(it) }

        val usableNodes = nodes.filter { isUsableEgressNode(it) }
        val candidatePool = if (usableNodes.isNotEmpty()) usableNodes else nodes

        val priorityTiers = candidatePool
            .groupBy { it.panelPriority ?: 1 }
            .toSortedMap()

        val semaphore = Semaphore(6)

        // Waterfall cascade: test each priority tier in order
        for ((tier, tierNodes) in priorityTiers) {
            val tierName = tierNodes.firstOrNull()?.panelName ?: "اولویت $tier"
            val isTopPriority = (tier == priorityTiers.firstKey())
            val tcpTimeout = if (isTopPriority) 2500 else 1200
            val realDelayTimeout = if (isTopPriority) 7000L else 3500L

            Log.i(TAG, "findFastestNode: Checking Priority Tier $tier ($tierName, ${tierNodes.size} nodes, timeout: ${realDelayTimeout}ms)")

            val tcpResults = tierNodes.map { node ->
                async {
                    val tcp = testTcpLatency(node.server, node.port, tcpTimeout)
                    Pair(node, tcp)
                }
            }.awaitAll()

            val responsive = tcpResults.filter { it.second > 0 }.sortedBy { it.second }.map { it.first }
            val poolToTest = if (responsive.isNotEmpty()) responsive.take(8) else tierNodes.take(8)

            val realResults = poolToTest.map { node ->
                async {
                    semaphore.withPermit {
                        val realDelay = measureRealDelay(node, realDelayTimeout)
                        node.latencyMs = realDelay
                        Pair(node, realDelay)
                    }
                }
            }.awaitAll()

            val workingNode = realResults.filter { it.second > 0 }.minByOrNull { it.second }
            if (workingNode != null) {
                Log.i(TAG, "findFastestNode: Selected fastest verified proxy in Priority Tier $tier: [${workingNode.first.remark}] with REAL delay ${workingNode.second}ms")
                return@withContext workingNode.first
            }

            Log.w(TAG, "findFastestNode: All nodes in Priority Tier $tier failed real delay test. Cascading to next tier...")
        }

        val fallback = candidatePool[0]
        Log.w(TAG, "findFastestNode: No proxy passed real delay test across all tiers; using fallback [${fallback.remark}]")
        return@withContext fallback
    }

    /**
     * Backward compatible overload without context
     */
    suspend fun findFastestNode(nodes: List<VpnNode>): VpnNode {
        return findFastestNode(null, nodes)
    }

    /**
     * Auto-Failover Cascade when a link drops:
     * 1. Groups candidate nodes strictly by panel (prioritizing the current panel first, then by priority).
     * 2. Tests ALL links in the panel (no raw TCP prescan to avoid false negatives in filtered networks).
     * 3. As soon as ONE link connects with valid real delay (> 0):
     *    - Chooses it immediately!
     *    - Halts testing for that panel.
     *    - Returns the chosen link.
     * 4. If all links in the panel fail/timeout:
     *    - Goes to the next panel and tests all its links, and so on.
     */
    suspend fun findNextWorkingNodeCascade(
        allNodes: List<VpnNode>,
        currentNodeRemark: String?,
        isGeminiOptimizationEnabled: Boolean = false,
        onStatusLog: (String) -> Unit = {}
    ): VpnNode? = withContext(Dispatchers.IO) {
        val usable = allNodes.filter { isUsableEgressNode(it) && it.remark != currentNodeRemark }
        val candidatePool = if (usable.isNotEmpty()) usable else allNodes.filter { it.remark != currentNodeRemark }
        if (candidatePool.isEmpty()) {
            Log.w(TAG, "findNextWorkingNodeCascade: No candidate nodes found")
            return@withContext null
        }

        // Identify current node's panel (if known)
        val activeNode = allNodes.firstOrNull { it.remark == currentNodeRemark }
        val activePanelKey = activeNode?.let { it.panelId ?: it.panelName }

        data class PanelGroup(
            val priority: Int,
            val identifier: String,
            val name: String,
            val nodes: List<VpnNode>
        )

        val groupedPanels = candidatePool
            .groupBy { (it.panelPriority ?: 1) to (it.panelId ?: it.panelName ?: "default") }
            .map { (key, nodes) ->
                PanelGroup(
                    priority = key.first,
                    identifier = key.second,
                    name = nodes.firstOrNull()?.panelName ?: "پنل اولویت ${key.first}",
                    nodes = nodes
                )
            }

        // Current panel first, then ordered by panel priority (1 = highest, 2, 3...)
        val orderedPanels = groupedPanels.sortedWith(
            compareBy<PanelGroup> { panel ->
                if (activePanelKey != null && panel.identifier == activePanelKey) 0 else 1
            }.thenBy { it.priority }
        )

        Log.i(TAG, "findNextWorkingNodeCascade: Starting failover search across ${orderedPanels.size} panels...")

        for (panel in orderedPanels) {
            val panelName = panel.name
            val panelNodes = panel.nodes
            Log.i(TAG, ">> Failover: Testing ALL ${panelNodes.size} links in panel [$panelName] (Priority ${panel.priority})...")
            onStatusLog("🔍 بررسی تمام لینک‌های $panelName...")

            val chosenNode = testPanelLinksForFirstConnecting(
                nodes = panelNodes,
                isGeminiOptimizationEnabled = isGeminiOptimizationEnabled
            )

            if (chosenNode != null) {
                Log.i(TAG, ">> Failover SUCCESS: Connected to [${chosenNode.remark}] (${chosenNode.latencyMs}ms) in panel [$panelName]")
                return@withContext chosenNode
            }

            Log.w(TAG, ">> Failover: All ${panelNodes.size} links in panel [$panelName] failed. Moving to next panel...")
            onStatusLog("⚠️ هیچ‌یک از سرورهای $panelName پاسخ ندادند. در حال بررسی پنل بعدی...")
        }

        Log.w(TAG, "findNextWorkingNodeCascade: No responsive candidate found across all ${orderedPanels.size} panels")
        null
    }

    private suspend fun testPanelLinksForFirstConnecting(
        nodes: List<VpnNode>,
        isGeminiOptimizationEnabled: Boolean
    ): VpnNode? = coroutineScope {
        val foundNode = java.util.concurrent.atomic.AtomicReference<VpnNode?>(null)
        val concurrency = 3
        val semaphore = Semaphore(concurrency)

        val jobs = nodes.map { node ->
            launch {
                if (foundNode.get() != null) return@launch

                val delay = semaphore.withPermit {
                    if (foundNode.get() != null) return@withPermit -1L
                    measureRealDelay(node, timeoutMs = 3000L)
                }

                if (delay > 0) {
                    if (isGeminiOptimizationEnabled) {
                        val cached = com.asanvpn.app.data.NodeMetricsCache.getGeminiCompatibility(node)
                        val isGeminiOk = if (cached != null) {
                            cached.first
                        } else {
                            val measured = measureGeminiDelay(node, 3000L)
                            val ok = measured > 0
                            com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(node, ok, measured)
                            ok
                        }
                        if (!isGeminiOk) {
                            Log.w(TAG, "Failover: Node [${node.remark}] connected (${delay}ms) but failed Gemini requirement")
                            return@launch
                        }
                    }

                    node.latencyMs = delay
                    if (foundNode.compareAndSet(null, node)) {
                        Log.i(TAG, "Failover: Connecting link found: [${node.remark}] (${delay}ms)")
                        AppLogger.logLinkTest(node.remark, delay, isSuccess = true)
                    }
                } else {
                    AppLogger.logLinkTest(node.remark, -1L, isSuccess = false)
                }
            }
        }

        for (job in jobs) {
            if (foundNode.get() != null) {
                jobs.forEach { if (it.isActive) it.cancel() }
                break
            }
            job.join()
        }

        foundNode.get()
    }

    suspend fun findNextBestNode(
        nodes: List<VpnNode>,
        currentNodeRemark: String?,
        isGeminiOptimizationEnabled: Boolean = false
    ): VpnNode? {
        return findNextWorkingNodeCascade(
            allNodes = nodes,
            currentNodeRemark = currentNodeRemark,
            isGeminiOptimizationEnabled = isGeminiOptimizationEnabled
        )
    }

    /**
     * Measures true end-to-end HTTP round-trip latency through the proxy tunnel using Libv2ray.
     * Tries primary Cloudflare endpoint first, and automatically falls back to Google generate_204
     * if primary times out or is blocked.
     * Returns true latency in milliseconds if working, or -1L if broken/blocked.
     */
    suspend fun measureRealDelay(node: VpnNode, timeoutMs: Long = 3500L): Long = withContext(Dispatchers.IO) {
        val configJson = try {
            V2RayConfigBuilder.buildTestConfig(node)
        } catch (e: Exception) {
            return@withContext -1L
        }

        withTimeoutOrNull(timeoutMs) {
            // First attempt with fallback test endpoint (Google / gstatic - fastest & most reliable in Iran)
            try {
                val delay1 = Libv2ray.measureOutboundDelay(configJson, TEST_URL_FALLBACK)
                if (delay1 > 0) return@withTimeoutOrNull delay1
            } catch (_: Exception) {}

            // Second attempt with primary test endpoint (Cloudflare)
            try {
                val delay2 = Libv2ray.measureOutboundDelay(configJson, TEST_URL_PRIMARY)
                if (delay2 > 0) return@withTimeoutOrNull delay2
            } catch (_: Exception) {}

            -1L
        } ?: -1L
    }

    /**
     * Tests download throughput (MB/s) of candidate nodes in the background sequentially without disconnecting.
     * Uses a lightweight 4 MB payload per server (tested strictly one-by-one).
     * Takes up to 5 candidate nodes (including the currently active node).
     * If Gemini mode is enabled, only candidate nodes passing Gemini verification are considered.
     * Returns a candidate node if it is significantly faster (at least 25% and >= 0.5 MB/s) than the active node,
     * or null if the active node is already best or testing cannot find a better candidate.
     */
    suspend fun benchmarkCandidateThroughput(
        candidates: List<VpnNode>,
        activeNode: VpnNode,
        isGeminiOptimizationEnabled: Boolean = false,
        timeoutPerNodeMs: Long = 12000L
    ): VpnNode? = withContext(Dispatchers.IO) {
        if (candidates.size <= 1) return@withContext null

        Log.i(TAG, "Starting sequential download throughput benchmark (4MB) on ${candidates.size} nodes...")
        AppLogger.logUser("📊 شروع تست سرعت دانلود ۴ مگابایت سرورها به صورت نوبتی در پس‌زمینه...")

        // candidate remark -> speed in MB/s
        val speedResults = mutableMapOf<String, Double>()

        // Ensure activeNode is evaluated first as baseline
        val orderedCandidates = mutableListOf<VpnNode>()
        orderedCandidates.add(activeNode)
        for (c in candidates) {
            if (c.remark != activeNode.remark && orderedCandidates.size < 5) {
                orderedCandidates.add(c)
            }
        }

        // Sequential one-by-one testing
        for ((index, node) in orderedCandidates.withIndex()) {
            if (!isActive) return@withContext null

            // 1. Check cached download speed first (reused if link is unchanged from panel)
            val cachedSpeed = com.asanvpn.app.data.NodeMetricsCache.getSpeed(node)
            if (cachedSpeed != null && cachedSpeed > 0.0) {
                val roundedCached = (cachedSpeed * 10).toInt() / 10.0
                speedResults[node.remark] = cachedSpeed
                Log.i(TAG, "Using cached throughput for [${node.remark}]: ${roundedCached} MB/s (unchanged from panel)")
                AppLogger.logUser("⚡ سرعت ذخیره‌شده [${node.remark}]: ${roundedCached} MB/s (از کش - بدون نیاز به دانلود مجدد)")
                continue
            }

            AppLogger.logUser("⏳ [${index + 1}/${orderedCandidates.size}] در حال سنجش سرعت ۴ مگابایت [${node.remark}]...")

            if (isGeminiOptimizationEnabled) {
                val cachedGemini = com.asanvpn.app.data.NodeMetricsCache.getGeminiCompatibility(node)
                val geminiDelay = if (cachedGemini != null) {
                    if (cachedGemini.first) cachedGemini.second else -1L
                } else {
                    val delay = measureGeminiDelay(node, 3000L)
                    com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(node, delay > 0, delay)
                    delay
                }
                if (geminiDelay <= 0) {
                    AppLogger.logUser("⚠️ سرور [${node.remark}] فاقد دسترسی کامل به Gemini (رد شد)")
                    speedResults[node.remark] = 0.0
                    continue
                }
            }

            val configJson = try {
                V2RayConfigBuilder.buildTestConfig(node)
            } catch (e: Exception) {
                null
            }

            if (configJson == null) continue

            val durationMs = withTimeoutOrNull(timeoutPerNodeMs) {
                try {
                    val d1 = Libv2ray.measureOutboundDelay(configJson, SPEED_TEST_URL_PRIMARY)
                    if (d1 > 0) return@withTimeoutOrNull d1
                } catch (_: Exception) {}

                try {
                    val d2 = Libv2ray.measureOutboundDelay(configJson, SPEED_TEST_URL_FALLBACK)
                    if (d2 > 0) return@withTimeoutOrNull d2
                } catch (_: Exception) {}

                -1L
            } ?: -1L

            if (durationMs > 0) {
                val speedMBs = (4.0 / (durationMs / 1000.0))
                val roundedSpeed = (speedMBs * 10).toInt() / 10.0
                speedResults[node.remark] = speedMBs
                // Save to persistent cache so future runs reuse this result as long as link is unchanged
                com.asanvpn.app.data.NodeMetricsCache.saveSpeed(node, speedMBs)
                Log.i(TAG, "Throughput test [${node.remark}]: ${roundedSpeed} MB/s (${durationMs}ms) - Saved to cache")
                AppLogger.logUser("⚡ نتیجه دانلود [${node.remark}]: ${roundedSpeed} MB/s (ذخیره در کش)")
            } else {
                Log.w(TAG, "Throughput test [${node.remark}] timed out or failed")
                speedResults[node.remark] = 0.0
                AppLogger.logUser("⚠️ سنجش دانلود [${node.remark}] ناموفق بود")
            }
        }

        val activeSpeed = speedResults[activeNode.remark] ?: 0.0
        val bestEntry = speedResults.filter { it.value > 0.0 }.maxByOrNull { it.value }

        if (bestEntry != null && bestEntry.key != activeNode.remark) {
            val bestNode = orderedCandidates.firstOrNull { it.remark == bestEntry.key }
            val bestSpeed = bestEntry.value
            // Only switch if at least 25% faster and at least 0.5 MB/s difference
            if (bestNode != null && (bestSpeed > activeSpeed * 1.25) && (bestSpeed - activeSpeed >= 0.5)) {
                val roundedBest = (bestSpeed * 10).toInt() / 10.0
                val roundedActive = (activeSpeed * 10).toInt() / 10.0
                Log.i(TAG, "Throughput Winner: [${bestNode.remark}] (${roundedBest} MB/s vs active [${activeNode.remark}] ${roundedActive} MB/s)")
                AppLogger.logUser("🚀 سرور [${bestNode.remark}] با سرعت ${roundedBest} MB/s انتخاب شد (سریع‌تر از سرور فعلی با ${roundedActive} MB/s)")
                return@withContext bestNode
            }
        }

        val roundedActive = (activeSpeed * 10).toInt() / 10.0
        AppLogger.logUser("✅ بررسی سرعت دانلود تکمیل شد: سرور فعلی [${activeNode.remark}] با سرعت ${roundedActive} MB/s در وضعیت مطلوب قرار دارد.")
        return@withContext null
    }

    /**
     * Measures latency specifically to Google Gemini service via the candidate node tunnel.
     * Returns delay in ms if Gemini is reachable and unblocked, or -1 if blocked/error.
     */
    suspend fun measureGeminiDelay(node: VpnNode, timeoutMs: Long = 4000L): Long = withContext(Dispatchers.IO) {
        val configJson = try {
            V2RayConfigBuilder.buildTestConfig(node)
        } catch (e: Exception) {
            return@withContext -1L
        }

        withTimeoutOrNull(timeoutMs) {
            try {
                val d1 = Libv2ray.measureOutboundDelay(configJson, GEMINI_TEST_URL)
                if (d1 > 0) return@withTimeoutOrNull d1
            } catch (_: Exception) {}

            try {
                val d2 = Libv2ray.measureOutboundDelay(configJson, GEMINI_API_TEST_URL)
                if (d2 > 0) return@withTimeoutOrNull d2
            } catch (_: Exception) {}

            -1L
        } ?: -1L
    }

    /**
     * Live test from active connected device directly to Google Gemini.
     * Inspects redirects and HTTP response code to confirm zero geo-restrictions or 403 blocks.
     */
    suspend fun testLiveGeminiConnectivity(timeoutMs: Long = 5000L): GeminiCheckResult = withContext(Dispatchers.IO) {
        val start = System.currentTimeMillis()
        try {
            val client = OkHttpClient.Builder()
                .connectTimeout(timeoutMs, TimeUnit.MILLISECONDS)
                .readTimeout(timeoutMs, TimeUnit.MILLISECONDS)
                .followRedirects(true)
                .build()

            val req = Request.Builder()
                .url(GEMINI_TEST_URL)
                .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                .build()

            client.newCall(req).execute().use { resp ->
                val latency = System.currentTimeMillis() - start
                val code = resp.code
                val effectiveUrl = resp.request.url.toString()
                val body = resp.body?.string() ?: ""

                val isBlocked = effectiveUrl.contains("unavailable", ignoreCase = true) ||
                        code == 403 ||
                        body.contains("not available in your country", ignoreCase = true) ||
                        body.contains("not supported in your country", ignoreCase = true)

                if (isBlocked) {
                    return@withContext GeminiCheckResult(
                        isSuccess = false,
                        latencyMs = latency,
                        message = "این سرور با خطای کشور یا محدودیت گوگل جمینای مواجه است (کد $code)"
                    )
                }

                if (code in 200..399) {
                    return@withContext GeminiCheckResult(
                        isSuccess = true,
                        latencyMs = latency,
                        message = "اتصال پایدار و ۱۰۰٪ سازگار با Gemini (${latency}ms)"
                    )
                }

                return@withContext GeminiCheckResult(
                    isSuccess = false,
                    latencyMs = latency,
                    message = "پاسخ ناموفق از سرور جمینای: کد $code"
                )
            }
        } catch (e: Exception) {
            val latency = System.currentTimeMillis() - start
            return@withContext GeminiCheckResult(
                isSuccess = false,
                latencyMs = latency,
                message = "خطا در برقراری ارتباط با گوگل جمینای (${e.message ?: "تایم‌اوت"})"
            )
        }
    }

    /**
     * Measures the live realtime latency of the active connection while the VPN is ON.
     */
    suspend fun testConnectedRealLatency(timeoutMs: Long = 2000L): Long = withContext(Dispatchers.IO) {
        val coreDelay = withTimeoutOrNull(timeoutMs) {
            async(Dispatchers.IO) {
                try {
                    // Try gstatic first (Google 204 is faster & more reliable in Iran)
                    val d1 = V2RayCoreManager.measureDelay(TEST_URL_FALLBACK)
                    if (d1 > 0) return@async d1

                    // Fallback to Cloudflare
                    val d2 = V2RayCoreManager.measureDelay(TEST_URL_PRIMARY)
                    if (d2 > 0) return@async d2

                    -1L
                } catch (_: Exception) {
                    -1L
                }
            }.await()
        } ?: -1L

        coreDelay
    }

    private fun isUsableEgressNode(node: VpnNode): Boolean {
        // Exclude dummy or informational nodes (such as remarks with 👤, 📊, ⌛ or localhost/null IP)
        if (node.server == "127.0.0.1" || node.server == "0.0.0.0" || node.server.equals("localhost", ignoreCase = true) ||
            (node.server == "1.1.1.1" && node.port == 1080) || node.port <= 0) {
            return false
        }
        val remark = node.remark.trim()
        if (remark.startsWith("👤") || remark.startsWith("📊") || remark.startsWith("⌛") || remark.startsWith("⏳") ||
            (remark.contains("🔋") && (remark.contains("⌛") || remark.contains("⏳") || remark.contains("👤")))) {
            return false
        }

        // If node has Reality public key (pbk), it is an encrypted Reality tunnel, NOT plaintext!
        if (!node.pbk.isNullOrBlank()) {
            return true
        }

        // Plaintext nodes (security=none) cannot bypass DPI filtering
        val sec = node.security?.lowercase()?.trim() ?: "none"
        if (sec == "none" || sec.isEmpty()) {
            return false
        }
        val s = node.server.lowercase().trim()
        if (s.startsWith("104.") || s.startsWith("172.67.") || s.startsWith("162.159.")) {
            return false
        }
        return true
    }

    private fun testTcpLatency(host: String, port: Int, timeoutMs: Int): Long {
        val start = System.currentTimeMillis()
        return try {
            Socket().use { socket ->
                socket.connect(InetSocketAddress(host, port), timeoutMs)
                System.currentTimeMillis() - start
            }
        } catch (e: Exception) {
            -1L // Timed out or connection refused
        }
    }
}
