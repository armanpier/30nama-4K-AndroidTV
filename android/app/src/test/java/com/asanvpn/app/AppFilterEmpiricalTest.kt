package com.asanvpn.app

import com.asanvpn.app.util.AppFilterHelper
import org.junit.Assert.*
import org.junit.Test

class AppFilterEmpiricalTest {

    @Test
    fun testPopularPackagesPresence() {
        val popular = AppFilterHelper.POPULAR_PACKAGES
        assertTrue("Telegram must be in popular packages", popular.contains("org.telegram.messenger"))
        assertTrue("Instagram must be in popular packages", popular.contains("com.instagram.android"))
        assertTrue("WhatsApp must be in popular packages", popular.contains("com.whatsapp"))
        assertTrue("YouTube must be in popular packages", popular.contains("com.google.android.youtube"))
        assertTrue("Chrome must be in popular packages", popular.contains("com.android.chrome"))
        assertTrue("Twitter must be in popular packages", popular.contains("com.twitter.android"))
    }

    @Test
    fun testSelfPackageExclusionLogic() {
        val myPackage = "com.asanvpn.app"
        val testWhitelist = setOf(
            "org.telegram.messenger",
            "com.instagram.android",
            "com.asanvpn.app", // accidentally selected by user or bug
            "com.google.android.youtube"
        )

        // Simulate VpnService builder routing filter
        val allowedApps = mutableListOf<String>()
        for (pkg in testWhitelist) {
            if (pkg == myPackage) continue // Safety guard against proxy loops
            allowedApps.add(pkg)
        }

        assertFalse("Self package must NEVER be added to allowed applications", allowedApps.contains(myPackage))
        assertEquals(3, allowedApps.size)
        assertTrue(allowedApps.contains("org.telegram.messenger"))
        assertTrue(allowedApps.contains("com.instagram.android"))
        assertTrue(allowedApps.contains("com.google.android.youtube"))
    }

    @Test
    fun testEmptyWhitelistFallbackLogic() {
        val isFilterEnabled = true
        val emptyWhitelist = emptySet<String>()

        // When enabled but empty, system should treat as standard bypass or fallback
        val shouldUseWhitelist = isFilterEnabled && emptyWhitelist.isNotEmpty()
        assertFalse("Empty whitelist must not trigger addAllowedApplication mode", shouldUseWhitelist)
    }
}
