package com.asanvpn.app.util

import android.content.Context
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.drawable.BitmapDrawable
import android.graphics.drawable.Drawable
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class AppFilterItem(
    val packageName: String,
    val name: String,
    val iconBitmap: Bitmap?,
    val isSystem: Boolean
)

object AppFilterHelper {

    val POPULAR_PACKAGES = setOf(
        "org.telegram.messenger",
        "org.telegram.plus",
        "org.telegram.messenger.web",
        "org.thunderdog.challegram",
        "nekox.messenger",
        "com.instagram.android",
        "com.whatsapp",
        "com.whatsapp.w4b",
        "com.google.android.youtube",
        "com.google.android.apps.youtube.music",
        "com.twitter.android",
        "com.android.chrome",
        "org.mozilla.firefox",
        "com.google.android.vending",
        "com.discord",
        "com.spotify.music"
    )

    private fun drawableToBitmap(drawable: Drawable): Bitmap? {
        return try {
            if (drawable is BitmapDrawable && drawable.bitmap != null) {
                drawable.bitmap
            } else {
                val width = if (drawable.intrinsicWidth > 0) drawable.intrinsicWidth.coerceIn(48, 128) else 96
                val height = if (drawable.intrinsicHeight > 0) drawable.intrinsicHeight.coerceIn(48, 128) else 96
                val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
                val canvas = Canvas(bitmap)
                drawable.setBounds(0, 0, canvas.width, canvas.height)
                drawable.draw(canvas)
                bitmap
            }
        } catch (e: Exception) {
            null
        }
    }

    suspend fun loadInstalledApps(context: Context): List<AppFilterItem> = withContext(Dispatchers.IO) {
        val pm = context.packageManager
        val myPkg = context.packageName
        val appMap = mutableMapOf<String, AppFilterItem>()

        // 1. Launcher activities (applications visible on user's home screen)
        try {
            val mainIntent = Intent(Intent.ACTION_MAIN, null).apply {
                addCategory(Intent.CATEGORY_LAUNCHER)
            }
            val launcherList = pm.queryIntentActivities(mainIntent, 0)
            for (resolveInfo in launcherList) {
                val pkg = resolveInfo.activityInfo?.packageName ?: continue
                if (pkg == myPkg) continue
                if (appMap.containsKey(pkg)) continue

                try {
                    val appInfo = pm.getApplicationInfo(pkg, 0)
                    val label = pm.getApplicationLabel(appInfo).toString()
                    val icon = try { drawableToBitmap(pm.getApplicationIcon(appInfo)) } catch (e: Exception) { null }
                    val isSystem = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                    appMap[pkg] = AppFilterItem(pkg, label, icon, isSystem)
                } catch (e: Exception) {
                    // Ignore
                }
            }
        } catch (e: Exception) {
            // Ignore
        }

        // 2. Non-system installed applications not caught by launcher filter
        try {
            val allApps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
            for (appInfo in allApps) {
                val pkg = appInfo.packageName
                if (pkg == myPkg) continue
                if (appMap.containsKey(pkg)) continue

                val isSystem = (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0
                if (!isSystem) {
                    try {
                        val label = pm.getApplicationLabel(appInfo).toString()
                        val icon = try { drawableToBitmap(pm.getApplicationIcon(appInfo)) } catch (e: Exception) { null }
                        appMap[pkg] = AppFilterItem(pkg, label, icon, isSystem = false)
                    } catch (e: Exception) {
                        // Ignore
                    }
                }
            }
        } catch (e: Exception) {
            // Ignore
        }

        // Return sorted: user apps first, then alphabetically by name
        appMap.values.sortedWith(
            compareBy<AppFilterItem> { it.isSystem }
                .thenBy(String.CASE_INSENSITIVE_ORDER) { it.name }
        )
    }
}
