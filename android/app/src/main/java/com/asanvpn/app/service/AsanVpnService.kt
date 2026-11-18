package com.asanvpn.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.core.app.NotificationCompat
import com.asanvpn.app.MainActivity
import com.asanvpn.app.data.PreferencesManager
import com.asanvpn.app.data.VpnRepository
import com.asanvpn.app.service.v2ray.V2RayCoreManager
import com.asanvpn.app.util.AppLogger
import com.asanvpn.app.util.IranAppBypassHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class AsanVpnService : VpnService() {

    private var vpnInterface: ParcelFileDescriptor? = null
    private val serviceScope = CoroutineScope(Dispatchers.IO + Job())
    private lateinit var prefs: PreferencesManager
    private var sessionValidatorJob: Job? = null
    private var healthMonitorJob: Job? = null

    companion object {
        const val ACTION_CONNECT = "com.asanvpn.app.CONNECT"
        const val ACTION_DISCONNECT = "com.asanvpn.app.DISCONNECT"
        const val ACTION_SWITCH_CONFIG = "com.asanvpn.app.SWITCH_CONFIG"
        const val EXTRA_CONFIG = "com.asanvpn.app.EXTRA_CONFIG"
        const val NOTIFICATION_CHANNEL_ID = "asan_vpn_channel"
        const val NOTIFICATION_ID = 1001

        private val _vpnRunningState = MutableStateFlow(false)
        val vpnRunningState: StateFlow<Boolean> = _vpnRunningState.asStateFlow()

        val currentServerRemarkFlow = MutableStateFlow("")
        val currentServerPingFlow = MutableStateFlow(0L)

        var isRunning: Boolean
            get() = _vpnRunningState.value
            private set(value) {
                _vpnRunningState.value = value
            }
    }

    override fun onCreate() {
        super.onCreate()
        prefs = PreferencesManager(this)
        createNotificationChannel()
        V2RayCoreManager.initCore(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_CONNECT -> {
                val config = intent.getStringExtra(EXTRA_CONFIG) ?: prefs.activeV2RayConfig
                if (isRunning) {
                    switchVpnConfig(config)
                } else {
                    startVpnTunnel(config)
                }
            }
            ACTION_SWITCH_CONFIG -> {
                val config = intent.getStringExtra(EXTRA_CONFIG) ?: prefs.activeV2RayConfig
                switchVpnConfig(config)
            }
            ACTION_DISCONNECT -> {
                stopVpnTunnel()
            }
        }
        return START_NOT_STICKY
    }

    private fun switchVpnConfig(configJson: String?) {
        if (!isRunning || vpnInterface == null || configJson.isNullOrBlank()) {
            startVpnTunnel(configJson)
            return
        }
        try {
            val tunFd = vpnInterface!!.fd
            Log.i("AsanVpnService", "Seamlessly switching V2Ray core to fastest proxy on tunFd=$tunFd")
            val switched = V2RayCoreManager.startLoop(configJson, tunFd)
            Log.i("AsanVpnService", "V2Ray Core loop switched: $switched")
            if (switched) {
                prefs.activeV2RayConfig = configJson
                currentServerRemarkFlow.value = prefs.selectedServerRemark
                currentServerPingFlow.value = prefs.selectedServerPing
                updateNotification(prefs.selectedServerRemark)
            } else {
                Log.w("AsanVpnService", "Failed to switch V2Ray loop: core returned false")
            }
        } catch (e: Exception) {
            Log.e("AsanVpnService", "Failed to switch V2Ray config", e)
        }
    }

    private fun startVpnTunnel(configJson: String?) {
        if (isRunning) return
        if (configJson.isNullOrBlank()) {
            Log.e("AsanVpnService", "Cannot start VPN: Xray config is null or blank")
            return
        }

        try {
            val builder = Builder()
                .setSession("آسان وی‌پی‌ان")
                .setMtu(1400)
                .addAddress("172.19.0.1", 30)
                .addDnsServer("1.1.1.1")
                .addDnsServer("8.8.8.8")
                .addRoute("0.0.0.0", 0)

            // Trap and absorb all IPv6 traffic to prevent IPv6 leaks to Iranian cellular carriers (MCI / Irancell)
            try {
                builder.addAddress("fdfe:dcba:9876::1", 126)
                builder.addRoute("::", 0)
            } catch (e: Exception) {
                Log.w("AsanVpnService", "Could not bind IPv6 route: ${e.message}")
            }

            val isFilterEnabled = prefs.isAppFilterEnabled
            val whitelist = prefs.appFilterWhitelist

            if (isFilterEnabled && whitelist.isNotEmpty()) {
                var allowedCount = 0
                for (pkg in whitelist) {
                    if (pkg == packageName) continue // Never allow self into tunnel to prevent routing loop
                    try {
                        builder.addAllowedApplication(pkg)
                        allowedCount++
                    } catch (e: PackageManager.NameNotFoundException) {
                        Log.w("AsanVpnService", "Allowed app not found on device: $pkg")
                    } catch (e: Exception) {
                        Log.w("AsanVpnService", "Could not add allowed app $pkg: ${e.message}")
                    }
                }
                Log.i("AsanVpnService", "App Filter (Whitelist) ACTIVE: $allowedCount apps routed through VPN")
                AppLogger.logUser("🛡️ فیلتر برنامه‌ها فعال است: ترافیک $allowedCount برنامه انتخابی از فیلترشکن عبور می‌کند")
            } else {
                try {
                    // Allow this application process to bypass the tunnel so Xray outbound connections don't loop
                    builder.addDisallowedApplication(packageName)
                } catch (e: Exception) {
                    Log.w("AsanVpnService", "Could not set addDisallowedApplication: ${e.message}")
                }

                // Exclude Iranian domestic applications from tunnel routing
                IranAppBypassHelper.applyDisallowedApplications(builder, this)
            }

            vpnInterface = builder.establish()
            if (vpnInterface == null) {
                Log.e("AsanVpnService", "Builder.establish() returned null")
                isRunning = false
                prefs.isConnected = false
                return
            }

            val pfd = vpnInterface!!
            val tunFd = pfd.fd

            // Start V2Ray/Xray Core loop with the TUN file descriptor
            val coreStarted = V2RayCoreManager.startLoop(configJson, tunFd)
            Log.i("AsanVpnService", "V2Ray Core started: $coreStarted on tunFd=$tunFd")

            if (!coreStarted) {
                Log.e("AsanVpnService", "CRITICAL: V2Ray Core failed to start! Tearing down tunnel...")
                stopVpnTunnel()
                return
            }

            isRunning = true
            prefs.isConnected = true
            currentServerRemarkFlow.value = prefs.selectedServerRemark
            currentServerPingFlow.value = prefs.selectedServerPing
            updateNotification(prefs.selectedServerRemark)
            startHealthMonitor()

            // Periodic session check & live panel priority sync every 120 seconds
            sessionValidatorJob?.cancel()
            sessionValidatorJob = serviceScope.launch {
                val repo = VpnRepository(this@AsanVpnService)
                while (isRunning && isActive) {
                    kotlinx.coroutines.delay(120_000L) // 2 minutes
                    val pin = prefs.savedPin
                    if (pin.isNullOrBlank()) {
                        Log.i("AsanVpnService", "No saved PIN found, stopping VPN tunnel")
                        stopVpnTunnel()
                        break
                    }
                    val res = repo.syncWithWorker(pin)
                    res.onSuccess { response ->
                        val nodes = response.nodes
                        if (!nodes.isNullOrEmpty() && prefs.isAutoServerMode) {
                            checkAndApplyPrioritySwitch(nodes)
                        }
                    }
                    res.onFailure { error ->
                        val isRevoked = error is com.asanvpn.app.data.AuthRevokedException &&
                            (error.status == "invalid_pin" || error.status == "deleted" || error.status == "disabled")

                        if (isRevoked) {
                            Log.w("AsanVpnService", "Session revoked on server! Killing VPN tunnel...")
                            prefs.clearAll()
                            stopVpnTunnel()
                        }
                    }
                }
            }

            // Start foreground notification safely
            try {
                val notification = buildNotification(prefs.selectedServerRemark)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                    startForeground(
                        NOTIFICATION_ID,
                        notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
                    )
                } else {
                    startForeground(NOTIFICATION_ID, notification)
                }
            } catch (fgsEx: Exception) {
                fgsEx.printStackTrace()
            }

        } catch (e: Exception) {
            Log.e("AsanVpnService", "Exception starting VPN tunnel", e)
            stopVpnTunnel()
        }
    }

    private fun startHealthMonitor() {
        healthMonitorJob?.cancel()
        healthMonitorJob = serviceScope.launch(Dispatchers.IO) {
            var lastPingTestTime = 0L
            var consecutivePingFails = 0
            var isFailoverInProgress = false
            var lastDownlinkBytes = 0L
            var lastCheckTime = System.currentTimeMillis()

            Log.i("AsanVpnService", "Auto-Failover Health Monitor STARTED (10s live latency refresh & smart failover)")

            while (isRunning && isActive) {
                try {
                    if (!isFailoverInProgress) {
                        val currentRemark = prefs.selectedServerRemark
                        val stats = V2RayCoreManager.queryTrafficStats()
                        val now = System.currentTimeMillis()
                        val timeDelta = now - lastCheckTime
                        lastCheckTime = now

                        val downlinkDelta = if (stats != null && lastDownlinkBytes > 0) {
                            stats.downlinkBytes - lastDownlinkBytes
                        } else {
                            0L
                        }
                        if (stats != null) {
                            lastDownlinkBytes = stats.downlinkBytes
                        }

                        // Traffic flowing check (> 8 KB in interval)
                        val isTrafficFlowing = (downlinkDelta > 8192L && timeDelta < 4000L)
                        if (isTrafficFlowing) {
                            consecutivePingFails = 0
                        }

                        // Every 10 seconds: measure and broadcast real end-to-end tunnel latency
                        if (now - lastPingTestTime >= 10_000L) {
                            lastPingTestTime = now
                            val livePing = PingTester.testConnectedRealLatency(timeoutMs = 2500L)
                            if (livePing > 0) {
                                prefs.selectedServerPing = livePing
                                currentServerPingFlow.value = livePing
                                consecutivePingFails = 0
                                Log.i("AsanVpnService", "Live Ping [10s]: $livePing ms (Remark: $currentRemark)")
                            } else {
                                if (!isTrafficFlowing) {
                                    consecutivePingFails++
                                    Log.w("AsanVpnService", "Live Ping [10s] failed (attempt $consecutivePingFails)")
                                }
                            }
                        }

                        // Check failover criteria:
                        // In Manual Mode, user chose the server: never switch away unless completely unresponsive for >= 20s (2 consecutive failures) with zero traffic!
                        // In Auto Mode, switch if unresponsive for >= 10s with zero traffic.
                        val isAutoMode = prefs.isAutoServerMode
                        val failThreshold = if (isAutoMode) 1 else 2

                        if (consecutivePingFails >= failThreshold && !isTrafficFlowing) {
                            isFailoverInProgress = true
                            if (isAutoMode) {
                                AppLogger.logUser("⚠️ عدم دریافت پاسخ از سرور [$currentRemark]؛ در حال انتخاب سریع‌ترین سرور بعدی...")
                                AppLogger.logAdmin("Server [$currentRemark] unresponsive. Initiating auto-failover across panels...")
                            } else {
                                AppLogger.logUser("⚠️ سرور انتخابی [$currentRemark] قطع شد؛ در حال انتخاب سرور فعال جایگزین...")
                                AppLogger.logAdmin("Manual server [$currentRemark] unresponsive (20s). Failing over...")
                            }

                            val repo = VpnRepository(this@AsanVpnService)
                            val cachedNodes = repo.getCachedNodes()
                            if (cachedNodes.isNotEmpty()) {
                                val replacementNode = PingTester.findNextWorkingNodeCascade(
                                    allNodes = cachedNodes,
                                    currentNodeRemark = currentRemark,
                                    isGeminiOptimizationEnabled = prefs.isGeminiOptimizationEnabled,
                                    isVoiceCallOptimizationEnabled = prefs.isVoiceCallOptimizationEnabled,
                                    onStatusLog = { msg -> AppLogger.logUser(msg) }
                                )

                                if (replacementNode != null && isRunning) {
                                    AppLogger.logUser("🔄 اتصال با موفقیت به سرور [${replacementNode.remark}] منتقل شد (تاخیر: ${replacementNode.latencyMs}ms)")
                                    AppLogger.logAdmin("Auto-failover SUCCESS: Switched to [${replacementNode.remark}] in panel [${replacementNode.panelName}]")

                                    prefs.selectedServerRemark = replacementNode.remark
                                    prefs.selectedServerPing = replacementNode.latencyMs
                                    currentServerRemarkFlow.value = replacementNode.remark
                                    currentServerPingFlow.value = replacementNode.latencyMs
                                    updateNotification(replacementNode.remark)

                                    val newConfig = com.asanvpn.app.service.v2ray.V2RayConfigBuilder.buildConfig(replacementNode)
                                    prefs.activeV2RayConfig = newConfig
                                    switchVpnConfig(newConfig)
                                } else {
                                    AppLogger.logUser("⚠️ هیچ سرور فعالی در پنل‌ها پاسخ نداد. تلاش مجدد در چرخه بعدی...")
                                    AppLogger.logAdmin("Auto-failover: No responsive candidate found across all panels")
                                }
                            }
                            consecutivePingFails = 0
                            lastPingTestTime = System.currentTimeMillis()
                            isFailoverInProgress = false
                            kotlinx.coroutines.delay(4000L)
                        } else {
                            kotlinx.coroutines.delay(2000L)
                        }
                    } else {
                        consecutivePingFails = 0
                        kotlinx.coroutines.delay(2000L)
                    }
                } catch (e: Exception) {
                    Log.e("AsanVpnService", "Error in health monitor loop: ${e.message}", e)
                    kotlinx.coroutines.delay(2000L)
                }
            }
        }
    }

    private var isPrioritySwitching = false

    private fun checkAndApplyPrioritySwitch(nodes: List<com.asanvpn.app.data.models.VpnNode>) {
        if (!isRunning || !prefs.isAutoServerMode || isPrioritySwitching) return

        val currentRemark = prefs.selectedServerRemark
        val currentNode = nodes.firstOrNull { it.remark == currentRemark }
        val currentTier = currentNode?.panelPriority ?: 99

        val topPriority = nodes.mapNotNull { it.panelPriority }.minOrNull() ?: 1
        if (topPriority < currentTier) {
            isPrioritySwitching = true
            serviceScope.launch(Dispatchers.IO) {
                try {
                    val candidateNodes = nodes.filter { (it.panelPriority ?: 1) == topPriority }
                    val targetPanelName = candidateNodes.firstOrNull()?.panelName ?: "پنل اولویت $topPriority"

                    AppLogger.logUser("📡 اولویت پنل‌ها در داشبورد تغییر یافت؛ بررسی سرورهای $targetPanelName...")
                    AppLogger.logAdmin("Service: Live priority shift detected ($topPriority < $currentTier), testing $targetPanelName...")

                    val replacementNode = PingTester.findNextWorkingNodeCascade(
                        allNodes = candidateNodes,
                        currentNodeRemark = currentRemark,
                        isGeminiOptimizationEnabled = prefs.isGeminiOptimizationEnabled,
                        isVoiceCallOptimizationEnabled = prefs.isVoiceCallOptimizationEnabled,
                        onStatusLog = { msg -> AppLogger.logUser(msg) }
                    )

                    if (replacementNode != null && isRunning) {
                        AppLogger.logUser("🔄 اتصال با موفقیت به $targetPanelName - سرور [${replacementNode.remark}] منتقل شد (تاخیر: ${replacementNode.latencyMs}ms)")
                        AppLogger.logAdmin("Service: Priority switch SUCCESS to [${replacementNode.remark}] in panel [$targetPanelName]")

                        prefs.selectedServerRemark = replacementNode.remark
                        prefs.selectedServerPing = replacementNode.latencyMs
                        currentServerRemarkFlow.value = replacementNode.remark
                        currentServerPingFlow.value = replacementNode.latencyMs
                        updateNotification(replacementNode.remark)

                        val newConfig = com.asanvpn.app.service.v2ray.V2RayConfigBuilder.buildConfig(replacementNode)
                        prefs.activeV2RayConfig = newConfig
                        switchVpnConfig(newConfig)
                    } else {
                        AppLogger.logUser("⚠️ سرورهای $targetPanelName در حال حاضر پاسخ ندادند؛ حفظ اتصال روی سرور فعلی [${currentRemark}]")
                    }
                } finally {
                    isPrioritySwitching = false
                }
            }
        }
    }

    private fun updateNotification(serverRemark: String? = null) {
        if (!isRunning) return
        try {
            val notification = buildNotification(serverRemark)
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.notify(NOTIFICATION_ID, notification)
        } catch (e: Exception) {
            Log.w("AsanVpnService", "Could not update notification: ${e.message}")
        }
    }

    private fun stopVpnTunnel() {
        healthMonitorJob?.cancel()
        healthMonitorJob = null
        sessionValidatorJob?.cancel()
        sessionValidatorJob = null

        isRunning = false
        prefs.isConnected = false
        currentServerPingFlow.value = 0L

        try {
            V2RayCoreManager.stopLoop()
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            vpnInterface?.close()
            vpnInterface = null
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            stopForeground(true)
        } catch (e: Exception) {
            // Ignore
        }
        stopSelf()
    }

    override fun onDestroy() {
        super.onDestroy()
        stopVpnTunnel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "وضعیت اتصال آسان وی‌پی‌ان",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "نمایش وضعیت روشن بودن اینترنت امن"
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(serverRemark: String? = null): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val piFlags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val openAppPendingIntent = PendingIntent.getActivity(
            this, 0, openAppIntent, piFlags
        )

        val disconnectIntent = Intent(this, AsanVpnService::class.java).apply {
            action = ACTION_DISCONNECT
        }
        val disconnectPendingIntent = PendingIntent.getService(
            this, 1, disconnectIntent, piFlags
        )

        val remark = serverRemark ?: prefs.selectedServerRemark
        val content = if (remark.isNotBlank()) "متصل به: $remark" else "اینترنت شما امن و متصل است"

        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_lock)
            .setContentTitle("آسان وی‌پی‌ان روشن است")
            .setContentText(content)
            .setContentIntent(openAppPendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "قطع اتصال", disconnectPendingIntent)
            .setOngoing(true)
            .build()
    }
}
