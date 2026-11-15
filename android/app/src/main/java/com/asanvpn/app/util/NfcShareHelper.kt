package com.asanvpn.app.util

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.os.Build
import android.provider.Settings
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File

object NfcShareHelper {

    fun isNfcSupported(context: Context): Boolean {
        return try {
            val adapter = NfcAdapter.getDefaultAdapter(context)
            adapter != null
        } catch (_: Exception) {
            false
        }
    }

    fun isNfcEnabled(context: Context): Boolean {
        return try {
            val adapter = NfcAdapter.getDefaultAdapter(context)
            adapter != null && adapter.isEnabled
        } catch (_: Exception) {
            false
        }
    }

    fun openNfcSettings(context: Context) {
        try {
            val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                Intent(Settings.ACTION_NFC_SETTINGS)
            } else {
                Intent(Settings.ACTION_WIRELESS_SETTINGS)
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        } catch (e: Exception) {
            try {
                val intent = Intent(Settings.ACTION_SETTINGS)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
            } catch (_: Exception) {}
        }
    }

    /**
     * Registers an NDEF push message on the Activity so touching devices transmits the URL & opens the download.
     * Uses reflection to maintain compatibility with all compileSdk and runtime levels.
     */
    fun setupNdefPush(activity: Activity, url: String) {
        try {
            val adapter = NfcAdapter.getDefaultAdapter(activity) ?: return
            if (adapter.isEnabled) {
                val uriRecord = NdefRecord.createUri(url)
                val aarRecord = NdefRecord.createApplicationRecord(activity.packageName)
                val ndefMessage = NdefMessage(arrayOf(uriRecord, aarRecord))
                try {
                    val method = adapter.javaClass.getMethod(
                        "setNdefPushMessage",
                        NdefMessage::class.java,
                        Activity::class.java
                    )
                    method.invoke(adapter, ndefMessage, activity)
                } catch (_: Exception) {}
            }
        } catch (_: Exception) {}
    }

    fun copyToClipboard(context: Context, text: String, label: String = "لینک دانلود آسان وی‌پی‌ان") {
        try {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            val clip = ClipData.newPlainText(label, text)
            clipboard?.setPrimaryClip(clip)
            Toast.makeText(context, "لینک دانلود مستقیم در کلیپ‌بورد کپی شد", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(context, "خطا در کپی لینک", Toast.LENGTH_SHORT).show()
        }
    }

    fun shareTextLink(context: Context, url: String) {
        try {
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_SUBJECT, "دانلود آسان وی‌پی‌ان")
                putExtra(
                    Intent.EXTRA_TEXT,
                    "دانلود مستقیم آسان وی‌پی‌ان (نسخه اختصاصی بدون فیلتر و پرسرعت):\n$url"
                )
            }
            val chooser = Intent.createChooser(intent, "اشتراک‌گذاری آسان وی‌پی‌ان")
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(chooser)
        } catch (_: Exception) {}
    }

    /**
     * Copies current running APK to cache and shares via Android system share sheet
     * (allows Quick Share / Nearby Share / Bluetooth offline transmission).
     */
    fun shareApkFile(context: Context) {
        try {
            val appInfo = context.applicationInfo
            val sourceApk = File(appInfo.sourceDir)
            if (!sourceApk.exists()) {
                Toast.makeText(context, "فایل نصبی یافت نشد", Toast.LENGTH_SHORT).show()
                return
            }

            val cacheDir = File(context.cacheDir, "shared_apk")
            if (!cacheDir.exists()) cacheDir.mkdirs()
            val targetApk = File(cacheDir, "AsanVPN-Universal.apk")

            if (!targetApk.exists() || targetApk.length() != sourceApk.length()) {
                sourceApk.copyTo(targetApk, overwrite = true)
            }
            targetApk.setReadable(true, false)

            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                targetApk
            )

            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "application/vnd.android.package-archive"
                putExtra(Intent.EXTRA_STREAM, uri)
                putExtra(Intent.EXTRA_SUBJECT, "فایل نصبی آسان وی‌پی‌ان")
                putExtra(
                    Intent.EXTRA_TEXT,
                    "فایل نصبی نسخه Universal آسان وی‌پی‌ان (قابل نصب روی تمام گوشی‌ها)"
                )
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }

            val chooser = Intent.createChooser(intent, "ارسال فایل نصبی برنامه")
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(chooser)
        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(context, "امکان ارسال مستقیم فایل وجود ندارد. لینک اشتراک‌گذاری شد.", Toast.LENGTH_SHORT).show()
            shareTextLink(context, "https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/download")
        }
    }
}
