package com.asanvpn.app.data

import android.content.Context
import com.asanvpn.app.data.models.VpnNode
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap

data class CachedNodeMetric(
    val linkSignature: String,
    var server: String? = null,
    var port: Int? = null,
    var remark: String? = null,
    var speedMBs: Double? = null,
    var speedTestedAt: Long = 0L,
    var isGeminiCompatible: Boolean? = null,
    var geminiLatencyMs: Long = -1L,
    var geminiTestedAt: Long = 0L,
    var isVoiceCallCompatible: Boolean? = null,
    var voiceCallTestedAt: Long = 0L,
    var latencyMs: Long? = null,
    var latencyTestedAt: Long = 0L
)

/**
 * High-performance, persistent cache for per-link speed throughput and Gemini AI connectivity tests.
 * Indexed by canonical link signature (hash of full link parameters).
 * As long as the link parameters have not changed from the panel side, the cached metrics are reused,
 * preventing redundant 4MB downloads or recurring Gemini test pings.
 */
object NodeMetricsCache {
    private val gson = Gson()
    private val memoryCache = ConcurrentHashMap<String, CachedNodeMetric>()
    private var prefsManager: PreferencesManager? = null
    @Volatile
    private var isLoaded = false

    fun init(context: Context) {
        if (prefsManager == null) {
            prefsManager = PreferencesManager(context.applicationContext)
        }
        loadFromDisk()
    }

    fun init(prefs: PreferencesManager) {
        prefsManager = prefs
        loadFromDisk()
    }

    @Synchronized
    private fun loadFromDisk() {
        if (isLoaded) return
        val raw = prefsManager?.nodeMetricsCacheJson
        if (!raw.isNullOrBlank()) {
            try {
                val type = object : TypeToken<Map<String, CachedNodeMetric>>() {}.type
                val map: Map<String, CachedNodeMetric> = gson.fromJson(raw, type)
                memoryCache.putAll(map)
            } catch (_: Exception) {}
        }
        isLoaded = true
    }

    @Synchronized
    private fun persistToDisk() {
        try {
            val json = gson.toJson(memoryCache)
            prefsManager?.nodeMetricsCacheJson = json
        } catch (_: Exception) {}
    }

    /**
     * Produces a deterministic unique SHA-256 signature for this link configuration from the panel.
     * If the panel updates the link (port, IP, UUID, security, SNI, path, pbk, sid, flow, etc.),
     * this signature changes automatically, invalidating the old cache.
     */
    fun getSignature(node: VpnNode): String {
        val raw = node.rawLink?.trim()
        if (!raw.isNullOrBlank()) {
            val base = raw.substringBefore("#")
            return hashString(base)
        }
        val canonical = "${node.protocol}://${node.server}:${node.port}/${node.uuid ?: node.password ?: ""}?type=${node.type}&security=${node.security}&sni=${node.sni}&pbk=${node.pbk}&sid=${node.sid}&path=${node.path}&headerType=${node.headerType}&encryption=${node.encryption}&flow=${node.flow}"
        return hashString(canonical)
    }

    private fun hashString(input: String): String {
        return try {
            val bytes = MessageDigest.getInstance("SHA-256").digest(input.toByteArray(Charsets.UTF_8))
            bytes.joinToString("") { "%02x".format(it) }
        } catch (_: Exception) {
            input.hashCode().toString()
        }
    }

    fun getSpeed(node: VpnNode): Double? {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache[sig]
        if (entry?.speedMBs != null && entry.speedMBs!! > 0.0) {
            return entry.speedMBs
        }
        // Resilient fallback by exact server:port match (when rawLink/signature formatting differs slightly)
        if (node.server.isNotBlank() && node.port > 0) {
            val fallback = memoryCache.values.firstOrNull {
                it.server == node.server && it.port == node.port
            }
            if (fallback?.speedMBs != null && fallback.speedMBs!! > 0.0) {
                return fallback.speedMBs
            }
        }
        return null
    }

    fun saveSpeed(node: VpnNode, speedMBs: Double) {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache.getOrPut(sig) { CachedNodeMetric(linkSignature = sig) }
        entry.server = node.server
        entry.port = node.port
        entry.remark = node.remark
        entry.speedMBs = speedMBs
        entry.speedTestedAt = System.currentTimeMillis()
        persistToDisk()
    }

    fun getGeminiCompatibility(node: VpnNode): Pair<Boolean, Long>? {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache[sig] ?: return null
        val comp = entry.isGeminiCompatible ?: return null
        return Pair(comp, entry.geminiLatencyMs)
    }

    fun saveGeminiCompatibility(node: VpnNode, isCompatible: Boolean, latencyMs: Long) {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache.getOrPut(sig) { CachedNodeMetric(linkSignature = sig) }
        entry.isGeminiCompatible = isCompatible
        entry.geminiLatencyMs = latencyMs
        entry.geminiTestedAt = System.currentTimeMillis()
        persistToDisk()
    }

    fun clearGeminiCache() {
        ensureLoaded()
        for (entry in memoryCache.values) {
            entry.isGeminiCompatible = null
            entry.geminiLatencyMs = -1L
            entry.geminiTestedAt = 0L
        }
        persistToDisk()
    }

    fun getVoiceCallCompatibility(node: VpnNode): Boolean? {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache[sig] ?: return null
        return entry.isVoiceCallCompatible
    }

    fun saveVoiceCallCompatibility(node: VpnNode, isCompatible: Boolean) {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache.getOrPut(sig) { CachedNodeMetric(linkSignature = sig) }
        entry.isVoiceCallCompatible = isCompatible
        entry.voiceCallTestedAt = System.currentTimeMillis()
        persistToDisk()
    }

    fun getLatency(node: VpnNode, maxAgeMs: Long = 900_000L): Long? {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache[sig]
        val lat = entry?.latencyMs
        if (lat != null && lat > 0) {
            if (maxAgeMs <= 0 || System.currentTimeMillis() - entry.latencyTestedAt <= maxAgeMs) {
                return lat
            }
        }
        if (node.server.isNotBlank() && node.port > 0) {
            val fallback = memoryCache.values.firstOrNull {
                it.server == node.server && it.port == node.port
            }
            val fallbackLat = fallback?.latencyMs
            if (fallbackLat != null && fallbackLat > 0) {
                if (maxAgeMs <= 0 || System.currentTimeMillis() - fallback.latencyTestedAt <= maxAgeMs) {
                    return fallbackLat
                }
            }
        }
        return null
    }

    fun saveLatency(node: VpnNode, latencyMs: Long) {
        ensureLoaded()
        val sig = getSignature(node)
        val entry = memoryCache.getOrPut(sig) { CachedNodeMetric(linkSignature = sig) }
        entry.server = node.server
        entry.port = node.port
        entry.remark = node.remark
        entry.latencyMs = latencyMs
        entry.latencyTestedAt = System.currentTimeMillis()
        persistToDisk()
    }

    fun clearVoiceCallCache() {
        ensureLoaded()
        for (entry in memoryCache.values) {
            entry.isVoiceCallCompatible = null
            entry.voiceCallTestedAt = 0L
        }
        persistToDisk()
    }

    private fun ensureLoaded() {
        if (!isLoaded) {
            loadFromDisk()
        }
    }

    fun clearAll() {
        memoryCache.clear()
        persistToDisk()
    }
}
