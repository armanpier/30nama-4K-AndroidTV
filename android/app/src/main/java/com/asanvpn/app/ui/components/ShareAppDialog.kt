package com.asanvpn.app.ui.components

import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.asanvpn.app.ui.theme.*
import com.asanvpn.app.util.NfcShareHelper
import com.asanvpn.app.util.QrCodeGenerator

@Composable
fun ShareAppDialog(
    downloadUrl: String = "https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/download",
    versionName: String = "Universal",
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val colors = LuxuryTheme.colors

    var selectedTab by remember { mutableStateOf(0) } // 0: QR Code, 1: NFC
    val isNfcSupported = remember { NfcShareHelper.isNfcSupported(context) }
    val isNfcEnabled = remember { NfcShareHelper.isNfcEnabled(context) }

    // Generate real, high-contrast, camera-friendly QR Code Bitmap via ZXing
    val qrBitmap: Bitmap? = remember(downloadUrl) {
        QrCodeGenerator.generate(downloadUrl, size = 640)
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            dismissOnBackPress = true,
            dismissOnClickOutside = true
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp)
                .luxuryCushion(shape = RoundedCornerShape(28.dp), elevation = 12.dp)
                .padding(22.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Header with Close Button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(36.dp)
                            .luxuryCushion(shape = CircleShape, elevation = 2.dp)
                            .clickable { onDismiss() },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "بستن",
                            tint = colors.textSecondary,
                            modifier = Modifier.size(18.dp)
                        )
                    }

                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text(
                            text = "اشتراک‌گذاری آسان وی‌پی‌ان",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Black,
                            color = colors.textPrimary,
                            textAlign = TextAlign.Center
                        )
                        Text(
                            text = "نسخه Universal (سازگار با همه گوشی‌ها)",
                            fontSize = 11.5.sp,
                            color = colors.textSecondary,
                            textAlign = TextAlign.Center
                        )
                    }

                    // Balance spacer
                    Spacer(modifier = Modifier.size(36.dp))
                }

                // Tab Switcher (QR Code vs NFC)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryWell(shape = RoundedCornerShape(16.dp))
                        .padding(4.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    // Tab 0: QR Code
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(12.dp))
                            .background(
                                if (selectedTab == 0) colors.skyBlue.copy(alpha = 0.18f) else Color.Transparent
                            )
                            .clickable { selectedTab = 0 }
                            .padding(vertical = 9.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.QrCode2,
                                contentDescription = null,
                                tint = if (selectedTab == 0) colors.skyBlue else colors.textMuted,
                                modifier = Modifier.size(17.dp)
                            )
                            Text(
                                text = "بارکد QR",
                                fontSize = 12.5.sp,
                                fontWeight = if (selectedTab == 0) FontWeight.Bold else FontWeight.Normal,
                                color = if (selectedTab == 0) colors.textPrimary else colors.textMuted
                            )
                        }
                    }

                    // Tab 1: NFC
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(12.dp))
                            .background(
                                if (selectedTab == 1) colors.jadeGreen.copy(alpha = 0.18f) else Color.Transparent
                            )
                            .clickable { selectedTab = 1 }
                            .padding(vertical = 9.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Nfc,
                                contentDescription = null,
                                tint = if (selectedTab == 1) colors.jadeGreen else colors.textMuted,
                                modifier = Modifier.size(17.dp)
                            )
                            Text(
                                text = "انتقال لمسی NFC",
                                fontSize = 12.5.sp,
                                fontWeight = if (selectedTab == 1) FontWeight.Bold else FontWeight.Normal,
                                color = if (selectedTab == 1) colors.textPrimary else colors.textMuted
                            )
                        }
                    }
                }

                // TAB CONTENT
                if (selectedTab == 0) {
                    // TAB 0: REAL QR CODE
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        // High-contrast clean white plate for 100% reliable camera scanning
                        Box(
                            modifier = Modifier
                                .size(210.dp)
                                .clip(RoundedCornerShape(20.dp))
                                .background(Color.White)
                                .border(2.dp, Color(0xFFE2E8F0), RoundedCornerShape(20.dp))
                                .padding(12.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            if (qrBitmap != null) {
                                Image(
                                    bitmap = qrBitmap.asImageBitmap(),
                                    contentDescription = "Real Universal APK QR Code",
                                    modifier = Modifier.fillMaxSize()
                                )
                            } else {
                                CircularProgressIndicator(
                                    color = colors.skyBlue,
                                    modifier = Modifier.size(36.dp)
                                )
                            }
                        }

                        Text(
                            text = "دوربین هر گوشی را مقابل این بارکد بگیرید تا لینک مستقیم دانلود آخرین نسخه Universal باز شود.",
                            fontSize = 11.5.sp,
                            color = colors.textSecondary,
                            textAlign = TextAlign.Center,
                            lineHeight = 17.sp,
                            modifier = Modifier.padding(horizontal = 8.dp)
                        )

                        // Quick Copy Pill
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryWell(shape = RoundedCornerShape(14.dp))
                                .clickable {
                                    NfcShareHelper.copyToClipboard(context, downloadUrl)
                                }
                                .padding(horizontal = 12.dp, vertical = 8.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.ContentCopy,
                                    contentDescription = "کپی لینک",
                                    tint = colors.skyBlue,
                                    modifier = Modifier.size(16.dp)
                                )
                                Text(
                                    text = downloadUrl.replace("https://", ""),
                                    fontSize = 10.5.sp,
                                    color = colors.textSecondary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier
                                        .weight(1f)
                                        .padding(horizontal = 8.dp),
                                    textAlign = TextAlign.Center
                                )
                                Text(
                                    text = "کپی",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.skyBlue
                                )
                            }
                        }
                    }
                } else {
                    // TAB 1: NFC TAP-TO-SHARE
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        // NFC Pulse Graphic Box
                        Box(
                            modifier = Modifier
                                .size(110.dp)
                                .luxuryWell(shape = CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(86.dp)
                                    .clip(CircleShape)
                                    .background(
                                        if (isNfcEnabled) colors.jadeGreen.copy(alpha = 0.2f)
                                        else colors.amberWarning.copy(alpha = 0.2f)
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Nfc,
                                    contentDescription = null,
                                    tint = if (isNfcEnabled) colors.jadeGreen else colors.amberWarning,
                                    modifier = Modifier.size(46.dp)
                                )
                            }
                        }

                        // NFC Status Description Card
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryWell(shape = RoundedCornerShape(16.dp))
                                .padding(12.dp)
                        ) {
                            Column(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                if (isNfcEnabled) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(8.dp)
                                                .clip(CircleShape)
                                                .background(colors.jadeGreen)
                                        )
                                        Text(
                                            text = "انتقال لمسی NFC آماده است",
                                            fontSize = 12.5.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = colors.jadeGreen
                                        )
                                    }
                                    Text(
                                        text = "پشت این گوشی را به پشت گوشی مقابل بچسبانید تا صفحه دانلود مستقیماً باز شود.",
                                        fontSize = 11.5.sp,
                                        color = colors.textSecondary,
                                        textAlign = TextAlign.Center,
                                        lineHeight = 17.sp
                                    )
                                } else if (isNfcSupported) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Warning,
                                            contentDescription = null,
                                            tint = colors.amberWarning,
                                            modifier = Modifier.size(15.dp)
                                        )
                                        Text(
                                            text = "سخت‌افزار NFC خاموش است",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = colors.amberWarning
                                        )
                                    }
                                    Text(
                                        text = "برای انتقال لمسی، لطفاً NFC را در تنظیمات گوشی روشن کنید.",
                                        fontSize = 11.sp,
                                        color = colors.textSecondary,
                                        textAlign = TextAlign.Center
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Box(
                                        modifier = Modifier
                                            .clip(RoundedCornerShape(10.dp))
                                            .background(colors.amberWarning.copy(alpha = 0.2f))
                                            .clickable { NfcShareHelper.openNfcSettings(context) }
                                            .padding(horizontal = 14.dp, vertical = 6.dp)
                                    ) {
                                        Text(
                                            text = "باز کردن تنظیمات NFC",
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = colors.amberWarning
                                        )
                                    }
                                } else {
                                    Text(
                                        text = "این گوشی فاقد سخت‌افزار NFC است",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = colors.textMuted,
                                        textAlign = TextAlign.Center
                                    )
                                    Text(
                                        text = "می‌توانید با دکمه زیر فایل نصبی برنامه را از طریق Quick Share یا بلوتوث ارسال کنید.",
                                        fontSize = 11.sp,
                                        color = colors.textSecondary,
                                        textAlign = TextAlign.Center
                                    )
                                }
                            }
                        }
                    }
                }

                // Divider
                HorizontalDivider(
                    color = colors.dividerSoft.copy(alpha = 0.4f),
                    thickness = 0.8.dp,
                    modifier = Modifier.padding(horizontal = 8.dp)
                )

                // BOTTOM ACTION BUTTONS
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // 1. Share Link Button
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(44.dp)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 4.dp)
                            .clickable {
                                NfcShareHelper.shareTextLink(context, downloadUrl)
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Share,
                                contentDescription = null,
                                tint = colors.skyBlue,
                                modifier = Modifier.size(16.dp)
                            )
                            Text(
                                text = "ارسال لینک",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary
                            )
                        }
                    }

                    // 2. Share Full APK File (Nearby Share / Bluetooth / Telegram)
                    Box(
                        modifier = Modifier
                            .weight(1.3f)
                            .height(44.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(
                                Brush.horizontalGradient(
                                    listOf(colors.jadeGreen, Color(0xFF10B981))
                                )
                            )
                            .clickable {
                                NfcShareHelper.shareApkFile(context)
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Send,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(16.dp)
                            )
                            Text(
                                text = "ارسال فایل نصبی (APK)",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                    }
                }
            }
        }
    }
}
