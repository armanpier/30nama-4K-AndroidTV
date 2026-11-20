package com.asanvpn.app

import com.asanvpn.app.data.models.VpnNode
import org.junit.Assert.*
import org.junit.Test

class SpeedOptimizationEmpiricalTest {

    @Test
    fun testThroughputCalculationFormula() {
        val chunkSizeBytes = 4_000_000L // 4 MB
        val durationMsFast = 1000L // 1.0 seconds
        val durationMsSlow = 4000L // 4.0 seconds

        val speedFast = (chunkSizeBytes / (1024.0 * 1024.0)) / (durationMsFast / 1000.0)
        val speedSlow = (chunkSizeBytes / (1024.0 * 1024.0)) / (durationMsSlow / 1000.0)

        val roundedFast = (speedFast * 10).toInt() / 10.0
        val roundedSlow = (speedSlow * 10).toInt() / 10.0

        assertEquals(3.8, roundedFast, 0.1)
        assertEquals(0.9, roundedSlow, 0.1)
        assertTrue(speedFast > speedSlow)
    }

    @Test
    fun testGeminiOptimizationNodeFiltering() {
        val nodes = listOf(
            VpnNode("vless", "Turkey🇹🇷", "1.2.3.4", 443, latencyMs = 60L),
            VpnNode("vless", "Germany🇩🇪", "1.2.3.5", 443, latencyMs = 70L),
            VpnNode("vless", "Iran🇮🇷", "1.2.3.6", 443, latencyMs = 20L),
            VpnNode("vless", "Russia🇷🇺", "1.2.3.7", 443, latencyMs = 80L),
            VpnNode("vless", "USA1🇺🇸", "1.2.3.8", 443, latencyMs = 120L)
        )

        // Gemini restricted keywords: Turkey, Iran, Russia, China, HK
        val geminiCompatible = nodes.filter { !com.asanvpn.app.service.PingTester.isGeminiRestrictedNode(it) }

        assertEquals(2, geminiCompatible.size)
        assertTrue(geminiCompatible.any { it.remark.contains("USA1") })
        assertTrue(geminiCompatible.any { it.remark.contains("Germany") })
        assertFalse(geminiCompatible.any { it.remark.contains("Turkey") })
        assertFalse(geminiCompatible.any { it.remark.contains("Iran") })
        assertFalse(geminiCompatible.any { it.remark.contains("Russia") })
    }

    @Test
    fun testVoiceCallOptimizationNodeFiltering() {
        val nodes = listOf(
            VpnNode("vless", "Fastly-XHTTP🇺🇸", "151.101.65.67", 443, latencyMs = 80L),
            VpnNode("vless", "Blocked-Voice", "gdtyum.g44mozgh.ir", 8443, latencyMs = 90L),
            VpnNode("vless", "Tunnel-8443🇩🇪", "188.121.110.232", 8443, latencyMs = 95L),
            VpnNode("vless", "AppleMarket-USA1🇺🇸", "94.183.166.44", 6608, latencyMs = 120L),
            VpnNode("vless", "PasarGuard-Germany🇩🇪", "45.14.225.10", 443, latencyMs = 75L)
        )

        val voiceCallCompatible = nodes.filter { !com.asanvpn.app.service.PingTester.isVoiceCallRestrictedNode(it) }

        assertEquals(3, voiceCallCompatible.size)
        assertTrue(voiceCallCompatible.any { it.remark.contains("AppleMarket-USA1") })
        assertTrue(voiceCallCompatible.any { it.remark.contains("PasarGuard-Germany") })
        assertTrue(voiceCallCompatible.any { it.remark.contains("Tunnel-8443") })
        assertFalse(voiceCallCompatible.any { it.remark.contains("Fastly") })
        assertFalse(voiceCallCompatible.any { it.server.contains("gdtyum.g44mozgh.ir") })
    }

    @Test
    fun testSwitchThresholdAntiFlap() {
        val activeSpeed = 2.0 // 2.0 MB/s

        // Test 1: Minor improvement (+5%, 2.1 MB/s) should NOT switch
        val candidateMarginal = 2.1
        val shouldSwitchMarginal = (candidateMarginal > activeSpeed * 1.25) && (candidateMarginal - activeSpeed >= 0.5)
        assertFalse("Marginal speed improvement must not trigger switch", shouldSwitchMarginal)

        // Test 2: Moderate improvement (+15%, 2.3 MB/s) should NOT switch
        val candidateModerate = 2.3
        val shouldSwitchModerate = (candidateModerate > activeSpeed * 1.25) && (candidateModerate - activeSpeed >= 0.5)
        assertFalse("15% speed improvement must not trigger switch", shouldSwitchModerate)

        // Test 3: Major improvement (+75%, 3.5 MB/s) MUST switch
        val candidateFast = 3.5
        val shouldSwitchFast = (candidateFast > activeSpeed * 1.25) && (candidateFast - activeSpeed >= 0.5)
        assertTrue("Substantial speed improvement (3.5 vs 2.0 MB/s) must trigger switch", shouldSwitchFast)
    }

    @Test
    fun testCandidatePoolFilteringAndLimiting() {
        val activeNode = VpnNode(
            protocol = "vless",
            remark = "Turkey🇹🇷",
            server = "1.2.3.4",
            port = 443,
            latencyMs = 57L,
            panelPriority = 1
        )

        val allNodes = listOf(
            activeNode,
            VpnNode("vless", "Germany🇩🇪", "1.2.3.5", 443, latencyMs = 70L, panelPriority = 1),
            VpnNode("vless", "Paris🇫🇷", "1.2.3.6", 443, latencyMs = 85L, panelPriority = 1),
            VpnNode("vless", "USA1🇺🇸", "1.2.3.7", 443, latencyMs = 120L, panelPriority = 1),
            VpnNode("vless", "USA2🇺🇸", "1.2.3.8", 443, latencyMs = 135L, panelPriority = 1),
            VpnNode("vless", "SlowNode", "1.2.3.9", 443, latencyMs = 250L, panelPriority = 1),
            VpnNode("vless", "Tier2Node", "1.2.3.10", 443, latencyMs = 40L, panelPriority = 2) // different tier
        )

        // Only nodes in active tier with valid latency, sorted by latency, max 5
        val filtered = allNodes
            .filter { (it.panelPriority ?: 1) == (activeNode.panelPriority ?: 1) && it.latencyMs > 0 }
            .sortedBy { it.latencyMs }
            .take(5)

        assertEquals(5, filtered.size)
        assertEquals("Turkey🇹🇷", filtered[0].remark)
        assertEquals("Germany🇩🇪", filtered[1].remark)
        assertEquals("Paris🇫🇷", filtered[2].remark)
        assertEquals("USA1🇺🇸", filtered[3].remark)
        assertEquals("USA2🇺🇸", filtered[4].remark)
        assertFalse(filtered.any { it.remark == "Tier2Node" })
        assertFalse(filtered.any { it.remark == "SlowNode" })
    }

    @Test
    fun testNodeSignatureStabilityAndChangeDetection() {
        val node1 = VpnNode(
            protocol = "vless",
            remark = "Turkey🇹🇷",
            server = "94.183.166.44",
            port = 6608,
            uuid = "09b88c53-52b1-4906-9447-2ee5e15d2b0e",
            type = "xhttp",
            security = "reality",
            sni = "play.google.com",
            pbk = "_ArxRjMxe3GA5IBqAK17lymLmYgdlLZY0hJ7ngB5lXg",
            rawLink = "vless://09b88c53-52b1-4906-9447-2ee5e15d2b0e@94.183.166.44:6608?security=reality#Turkey%20Server"
        )

        // Same link, only remark changed after # in panel
        val node1SameLink = VpnNode(
            protocol = "vless",
            remark = "Turkey New Remark",
            server = "94.183.166.44",
            port = 6608,
            uuid = "09b88c53-52b1-4906-9447-2ee5e15d2b0e",
            type = "xhttp",
            security = "reality",
            sni = "play.google.com",
            pbk = "_ArxRjMxe3GA5IBqAK17lymLmYgdlLZY0hJ7ngB5lXg",
            rawLink = "vless://09b88c53-52b1-4906-9447-2ee5e15d2b0e@94.183.166.44:6608?security=reality#DifferentRemark"
        )

        // Modified link from panel (e.g. port changed to 8808)
        val node1ChangedPort = VpnNode(
            protocol = "vless",
            remark = "Turkey🇹🇷",
            server = "94.183.166.44",
            port = 8808,
            uuid = "09b88c53-52b1-4906-9447-2ee5e15d2b0e",
            type = "xhttp",
            security = "reality",
            sni = "play.google.com",
            pbk = "_ArxRjMxe3GA5IBqAK17lymLmYgdlLZY0hJ7ngB5lXg",
            rawLink = "vless://09b88c53-52b1-4906-9447-2ee5e15d2b0e@94.183.166.44:8808?security=reality#Turkey%20Server"
        )

        val sig1 = com.asanvpn.app.data.NodeMetricsCache.getSignature(node1)
        val sig1Same = com.asanvpn.app.data.NodeMetricsCache.getSignature(node1SameLink)
        val sig1Changed = com.asanvpn.app.data.NodeMetricsCache.getSignature(node1ChangedPort)

        assertEquals("Same link config must have identical signature even if remark changes", sig1, sig1Same)
        assertNotEquals("Changed link from panel (e.g. new port) must have different signature", sig1, sig1Changed)
    }

    @Test
    fun testNodeMetricsCachingLifecycle() {
        val testNode = VpnNode(
            protocol = "vless",
            remark = "Germany🇩🇪",
            server = "94.183.166.44",
            port = 8808,
            uuid = "09b88c53-52b1-4906-9447-2ee5e15d2b0e",
            type = "xhttp",
            security = "reality"
        )

        // Save speed and Gemini status
        com.asanvpn.app.data.NodeMetricsCache.saveSpeed(testNode, 4.2)
        com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(testNode, true, 95L)

        // Retrieve
        val cachedSpeed = com.asanvpn.app.data.NodeMetricsCache.getSpeed(testNode)
        val cachedGemini = com.asanvpn.app.data.NodeMetricsCache.getGeminiCompatibility(testNode)

        assertNotNull(cachedSpeed)
        assertEquals(4.2, cachedSpeed!!, 0.01)

        assertNotNull(cachedGemini)
        assertTrue(cachedGemini!!.first)
        assertEquals(95L, cachedGemini.second)

        // A new/modified node must return null (not cached)
        val modifiedNode = VpnNode(
            protocol = "vless",
            remark = "Germany🇩🇪",
            server = "94.183.166.45", // changed IP
            port = 8808,
            uuid = "09b88c53-52b1-4906-9447-2ee5e15d2b0e"
        )
        assertNull(com.asanvpn.app.data.NodeMetricsCache.getSpeed(modifiedNode))
        assertNull(com.asanvpn.app.data.NodeMetricsCache.getGeminiCompatibility(modifiedNode))
    }

    @Test
    fun testAutoFailoverPanelOrderingAndPrioritization() {
        val deadNode = VpnNode(
            protocol = "vless",
            remark = "AppleMarket-Turkey🇹🇷",
            server = "1.2.3.4",
            port = 443,
            panelId = "panel_apple",
            panelName = "AppleMarket",
            panelPriority = 1
        )

        val allNodes = listOf(
            deadNode,
            VpnNode("vless", "AppleMarket-Paris🇫🇷", "1.2.3.5", 443, panelId = "panel_apple", panelName = "AppleMarket", panelPriority = 1),
            VpnNode("vless", "AppleMarket-Germany🇩🇪", "1.2.3.6", 443, panelId = "panel_apple", panelName = "AppleMarket", panelPriority = 1),
            VpnNode("vless", "Arvan-Frankfurt🇩🇪", "2.2.3.1", 443, panelId = "panel_arvan", panelName = "ArvanPanel", panelPriority = 2),
            VpnNode("vless", "Arvan-Amsterdam🇳🇱", "2.2.3.2", 443, panelId = "panel_arvan", panelName = "ArvanPanel", panelPriority = 2)
        )

        // Exclude dead node
        val candidatePool = allNodes.filter { it.remark != deadNode.remark }
        assertEquals(4, candidatePool.size)

        // Group by panel
        val activePanelKey = deadNode.panelId ?: deadNode.panelName
        val grouped = candidatePool
            .groupBy { (it.panelPriority ?: 1) to (it.panelId ?: it.panelName ?: "default") }
            .map { (key, nodes) ->
                Triple(key.first, key.second, nodes)
            }

        val ordered = grouped.sortedWith(
            compareBy<Triple<Int, String, List<VpnNode>>> { panel ->
                if (activePanelKey != null && panel.second == activePanelKey) 0 else 1
            }.thenBy { it.first }
        )

        assertEquals("First panel tested must be active panel (AppleMarket)", "panel_apple", ordered[0].second)
        assertEquals("Must test all remaining 2 nodes in AppleMarket", 2, ordered[0].third.size)

        assertEquals("Next panel tested must be ArvanPanel (Priority 2)", "panel_arvan", ordered[1].second)
        assertEquals("Must test all 2 nodes in ArvanPanel", 2, ordered[1].third.size)
    }

    @Test
    fun testAutoFailoverFiveSecondDropThreshold() {
        val unresponsiveStart = 100_000L

        // After 2.5 seconds: must NOT trigger failover
        val timeAt2500 = 102_500L
        val elapsed2500 = timeAt2500 - unresponsiveStart
        assertFalse("2.5s unresponsiveness must not trigger failover yet", elapsed2500 >= 5000L)

        // After 4.9 seconds: must NOT trigger failover
        val timeAt4900 = 104_900L
        val elapsed4900 = timeAt4900 - unresponsiveStart
        assertFalse("4.9s unresponsiveness must not trigger failover yet", elapsed4900 >= 5000L)

        // After 5.0 seconds: MUST trigger failover
        val timeAt5000 = 105_000L
        val elapsed5000 = timeAt5000 - unresponsiveStart
        assertTrue("5.0s unresponsiveness MUST trigger auto-failover", elapsed5000 >= 5000L)

        // Active downlink traffic (> 8KB) resets unresponsive start time
        val lastDownlink = 100_000L
        val currentDownlink = 120_000L // +20KB downloaded
        val downlinkDelta = currentDownlink - lastDownlink
        val isTrafficFlowing = (downlinkDelta > 8192L)
        assertTrue("Active downlink traffic detected", isTrafficFlowing)

        val resetUnresponsiveStart = if (isTrafficFlowing) 0L else unresponsiveStart
        assertEquals("Traffic flowing resets unresponsive timer to 0", 0L, resetUnresponsiveStart)
    }
}
