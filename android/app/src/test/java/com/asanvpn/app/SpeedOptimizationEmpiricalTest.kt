package com.asanvpn.app

import com.asanvpn.app.data.models.VpnNode
import org.junit.Assert.*
import org.junit.Test

class SpeedOptimizationEmpiricalTest {

    @Test
    fun testThroughputCalculationFormula() {
        val chunkSizeBytes = 10_000_000L // 10 MB
        val durationMsFast = 2000L // 2.0 seconds
        val durationMsSlow = 5000L // 5.0 seconds

        val speedFast = (chunkSizeBytes / (1024.0 * 1024.0)) / (durationMsFast / 1000.0)
        val speedSlow = (chunkSizeBytes / (1024.0 * 1024.0)) / (durationMsSlow / 1000.0)

        val roundedFast = (speedFast * 10).toInt() / 10.0
        val roundedSlow = (speedSlow * 10).toInt() / 10.0

        assertEquals(4.7, roundedFast, 0.1)
        assertEquals(1.9, roundedSlow, 0.1)
        assertTrue(speedFast > speedSlow)
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
}
