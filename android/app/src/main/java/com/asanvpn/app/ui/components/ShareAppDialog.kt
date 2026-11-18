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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.asanvpn.app.ui.theme.*
import com.asanvpn.app.util.AppShareHelper
import com.asanvpn.app.util.QrCodeGenerator

@Composable
fun ShareAppDialog(
    downloadUrl: String = "https://asanvpn-dashboard.armanpier-oxvrx.arvanedge.ir/download",
    versionName: String = "Universal",
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val colors = LuxuryTheme.colors

    val configuration = LocalConfiguration.current
    val screenHeight = configuration.screenHeightDp.dp
    val screenWidth = configuration.screenWidthDp.dp
    val isSmallScreen = screenHeight < 680.dp || screenWidth <= 365.dp

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
                .heightIn(max = screenHeight * 0.94f)
                .padding(horizontal = 4.dp)
                .luxuryCushion(
                    shape = RoundedCornerShape(if (isSmallScreen) 22.dp else 28.dp),
                    elevation = 12.dp
                )
                .padding(if (isSmallScreen) 12.dp else 22.dp)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(if (isSmallScreen) 10.dp else 16.dp)
            ) {
                // Header with Close Button
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(if (isSmallScreen) 32.dp else 36.dp)
                            .luxuryCushion(shape = CircleShape, elevation = 2.dp)
                            .clickable { onDismiss() },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "بستن",
                            tint = colors.textSecondary,
                            modifier = Modifier.size(if (isSmallScreen) 16.dp else 18.dp)
                        )
                    }

                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text(
                            text = "اشتراک‌گذاری آسان وی‌پی‌ان",
                            fontSize = if (isSmallScreen) 14.sp else 17.sp,
                            fontWeight = FontWeight.Black,
                            color = colors.textPrimary,
                            textAlign = TextAlign.Center
                        )
                        Text(
                            text = "نسخه Universal (سازگار با همه گوشی‌ها)",
                            fontSize = if (isSmallScreen) 10.sp else 11.5.sp,
                            color = colors.textSecondary,
                            textAlign = TextAlign.Center
                        )
                    }

                    // Balance spacer
                    Spacer(modifier = Modifier.size(if (isSmallScreen) 32.dp else 36.dp))
                }

                // QR CODE CONTENT
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(if (isSmallScreen) 10.dp else 14.dp)
                ) {
                    // High-contrast clean white plate for 100% reliable camera scanning
                    Box(
                        modifier = Modifier
                            .size(if (isSmallScreen) 160.dp else 220.dp)
                            .clip(RoundedCornerShape(if (isSmallScreen) 16.dp else 22.dp))
                            .background(Color.White)
                            .border(2.dp, Color(0xFFE2E8F0), RoundedCornerShape(if (isSmallScreen) 16.dp else 22.dp))
                            .padding(if (isSmallScreen) 10.dp else 14.dp),
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
                        fontSize = 12.sp,
                        color = colors.textSecondary,
                        textAlign = TextAlign.Center,
                        lineHeight = 18.sp,
                        modifier = Modifier.padding(horizontal = 6.dp)
                    )

                    // Quick Copy Pill
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .luxuryWell(shape = RoundedCornerShape(14.dp))
                            .clickable {
                                AppShareHelper.copyToClipboard(context, downloadUrl)
                            }
                            .padding(horizontal = 12.dp, vertical = 9.dp)
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
                                fontSize = 11.5.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.skyBlue
                            )
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
                                AppShareHelper.shareTextLink(context, downloadUrl)
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
                                AppShareHelper.shareApkFile(context)
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
