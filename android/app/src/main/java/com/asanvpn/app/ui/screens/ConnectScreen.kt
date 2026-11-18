package com.asanvpn.app.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.asanvpn.app.data.PreferencesManager
import com.asanvpn.app.data.VpnRepository
import com.asanvpn.app.data.models.ConnectionState
import com.asanvpn.app.data.models.VpnNode
import com.asanvpn.app.ui.components.AppFilterDialog
import com.asanvpn.app.ui.components.ServerSelectionDialog
import com.asanvpn.app.ui.theme.*
import com.asanvpn.app.util.AppLogger
import kotlinx.coroutines.delay

@Composable
fun ConnectScreen(
    userPin: String = "",
    userName: String,
    daysLeft: Int,
    trafficRemainingBytes: Long = 25L * 1024 * 1024 * 1024,
    trafficTotalBytes: Long = 30L * 1024 * 1024 * 1024,
    serverRemark: String = "🇩🇪 DE2 (سرور پیشنهادی)",
    serverPing: Long = 48L,
    connectionState: ConnectionState,
    downloadTraffic: String = "۰ B",
    uploadTraffic: String = "۰ B",
    downloadSpeed: String = "",
    uploadSpeed: String = "",
    appVersion: String = "1.3.32",
    newVersionAvailable: String? = null,
    isDarkMode: Boolean = false,
    availableNodes: List<VpnNode> = emptyList(),
    isAutoServerMode: Boolean = true,
    onToggleAutoServerMode: (Boolean) -> Unit = {},
    onSelectServerNode: (VpnNode) -> Unit = {},
    onToggleTheme: () -> Unit = {},
    onToggleConnect: () -> Unit,
    onContactSupport: () -> Unit = {},
    onCheckUpdate: () -> Unit = {},
    onShareClick: () -> Unit = {},
    onSaveAppFilter: (enabled: Boolean, whitelist: Set<String>, speedOptEnabled: Boolean, geminiOptEnabled: Boolean, voiceCallOptEnabled: Boolean) -> Unit = { _, _, _, _, _ -> },
    onChangePin: () -> Unit
) {
    val context = LocalContext.current
    val prefs = remember { PreferencesManager(context) }
    var showDebugDialog by remember { mutableStateOf(false) }
    var showAppFilterDialog by remember { mutableStateOf(false) }
    var showServerSelectDialog by remember { mutableStateOf(false) }
    var isAppFilterEnabled by remember { mutableStateOf(prefs.isAppFilterEnabled) }
    var appFilterWhitelist by remember { mutableStateOf(prefs.appFilterWhitelist) }
    var isSpeedOptimizationEnabled by remember { mutableStateOf(prefs.isSpeedOptimizationEnabled) }
    var isGeminiOptimizationEnabled by remember { mutableStateOf(prefs.isGeminiOptimizationEnabled) }
    var isVoiceCallOptimizationEnabled by remember { mutableStateOf(prefs.isVoiceCallOptimizationEnabled) }
    val isAppFilterActive = (isAppFilterEnabled && appFilterWhitelist.isNotEmpty()) || isSpeedOptimizationEnabled || isGeminiOptimizationEnabled || isVoiceCallOptimizationEnabled
    var showAdminAuthDialog by remember { mutableStateOf(false) }
    var adminPasswordInput by remember { mutableStateOf("") }
    var isAdminMode by remember { mutableStateOf(prefs.isAdmin) }

    val colors = LuxuryTheme.colors

    fun formatTrafficRemaining(bytes: Long): String {
        if (bytes < 0L) return "نامحدود"
        if (bytes == 0L) return "۰ GB"
        val gb = bytes / (1024.0 * 1024.0 * 1024.0)
        val mb = bytes / (1024.0 * 1024.0)
        return when {
            gb >= 1.0 -> String.format(java.util.Locale.US, "%.1f GB", gb)
            mb >= 1.0 -> String.format(java.util.Locale.US, "%.0f MB", mb)
            else -> "${bytes / 1024} KB"
        }
    }

    fun formatDuration(seconds: Long): String {
        val hrs = seconds / 3600
        val mins = (seconds % 3600) / 60
        val secs = seconds % 60
        return if (hrs > 0) {
            String.format("%02d:%02d:%02d", hrs, mins, secs)
        } else {
            String.format("%02d:%02d", mins, secs)
        }
    }

    val isTrafficUnlimited = trafficRemainingBytes < 0L || trafficTotalBytes <= 0L
    val isLowRemaining = !isTrafficUnlimited && trafficRemainingBytes in 1 until (1024L * 1024L * 1024L)
    val isExhaustedRemaining = !isTrafficUnlimited && trafficRemainingBytes == 0L

    // Live connection timer
    var connectedSeconds by remember { mutableLongStateOf(0L) }
    var connectingSeconds by remember { mutableLongStateOf(0L) }
    LaunchedEffect(connectionState) {
        if (connectionState == ConnectionState.CONNECTED) {
            connectedSeconds = 0L
            connectingSeconds = 0L
            while (true) {
                delay(1000)
                connectedSeconds++
            }
        } else if (connectionState == ConnectionState.CONNECTING) {
            connectingSeconds = 0L
            while (true) {
                delay(1000)
                connectingSeconds++
            }
        } else {
            connectedSeconds = 0L
            connectingSeconds = 0L
        }
    }

    // Infinite transitions for rotating silk light sheen & aura breathing
    val infiniteTransition = rememberInfiniteTransition(label = "luxury_orb")

    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.05f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "orb_pulse_scale"
    )

    val silkSheenRotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(6000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "orb_silk_sheen_rotation"
    )

    val isConnected = connectionState == ConnectionState.CONNECTED
    val isConnecting = connectionState == ConnectionState.CONNECTING

    val statusBadgeText = when (connectionState) {
        ConnectionState.DISCONNECTED -> "اتصال قطع شده است"
        ConnectionState.CONNECTING -> if (connectingSeconds >= 6) "درحال بررسی لینک‌ها..." else "در حال برقراری اتصال امن..."
        ConnectionState.CONNECTED -> "متصل و محافظت‌شده"
    }

    val statusSubText = when (connectionState) {
        ConnectionState.DISCONNECTED -> "برای محافظت و رمزگذاری ترافیک دکمه را لمس کنید"
        ConnectionState.CONNECTING -> "در حال یافتن بهترین مسیر ابری با پینگ پایین"
        ConnectionState.CONNECTED -> "ترافیک اینترنت شما کاملاً رمزگذاری شده است"
    }

    val statusTitleColor = when (connectionState) {
        ConnectionState.DISCONNECTED -> colors.textPrimary
        ConnectionState.CONNECTING -> colors.amberWarning
        ConnectionState.CONNECTED -> colors.jadeGreen
    }

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.backgroundBrush)
            .navigationBarsPadding()
    ) {
        val screenHeight = maxHeight
        val screenWidth = maxWidth
        val isSmallScreen = screenHeight < 680.dp || screenWidth <= 365.dp
        val isMediumScreen = screenHeight < 780.dp

        // Responsive dimensions tuned specifically for small 16:9 phones & large screens:
        val orbTotalSize = when {
            isSmallScreen -> 126.dp
            isMediumScreen -> 160.dp
            else -> 190.dp
        }
        val auraSize = orbTotalSize + 4.dp
        val torusSize = orbTotalSize - 12.dp
        val haloSize = torusSize - 20.dp
        val capSize = haloSize - 20.dp
        val powerIconSize = (capSize * 0.40f)

        val headerBtnSize = if (isSmallScreen) 32.dp else if (isMediumScreen) 36.dp else 40.dp
        val headerIconSize = if (isSmallScreen) 15.dp else if (isMediumScreen) 17.dp else 19.dp
        val sectionSpacing = if (isSmallScreen) 4.dp else if (isMediumScreen) 6.dp else 8.dp
        val orbVerticalSpacing = if (isSmallScreen) 5.dp else if (isMediumScreen) 8.dp else 12.dp

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = if (isSmallScreen) 10.dp else 14.dp, vertical = if (isSmallScreen) 4.dp else 8.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // ==================== TOP NAVIGATION BAR ====================
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = if (isSmallScreen) 2.dp else 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(if (isSmallScreen) 4.dp else 6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // 1. Info (i) Sculpted Pebble Button
                    Box(
                        modifier = Modifier
                            .size(headerBtnSize)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .clickable { showDebugDialog = true },
                        contentAlignment = Alignment.Center
                    ) {
                        Box(
                            modifier = Modifier
                                .size(if (isSmallScreen) 18.dp else 22.dp)
                                .clip(CircleShape)
                                .background(
                                    if (colors.isDark) Color(0xFF334155) else Color(0xFF475569)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = "i",
                                fontSize = if (isSmallScreen) 10.sp else 11.5.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = Color.White
                            )
                        }
                    }

                    // 2. Gear (Settings & App Filter Whitelist) Sculpted Pebble Button
                    Box(
                        modifier = Modifier
                            .size(headerBtnSize)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .clickable { showAppFilterDialog = true },
                        contentAlignment = Alignment.Center
                    ) {
                        Box(contentAlignment = Alignment.TopEnd) {
                            Icon(
                                imageVector = Icons.Default.Settings,
                                contentDescription = "فیلتر برنامه‌ها (App Filter)",
                                tint = if (isAppFilterActive) colors.jadeGreen else colors.textSecondary,
                                modifier = Modifier.size(headerIconSize)
                            )
                            if (isAppFilterActive) {
                                Box(
                                    modifier = Modifier
                                        .size(6.dp)
                                        .offset(x = 2.dp, y = (-2).dp)
                                        .clip(CircleShape)
                                        .background(colors.jadeGreen)
                                )
                            }
                        }
                    }

                    // 3. Luxury Theme Switcher (Light Porcelain <-> Dark Obsidian)
                    Box(
                        modifier = Modifier
                            .size(headerBtnSize)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .clickable { onToggleTheme() },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = if (colors.isDark) Icons.Default.LightMode else Icons.Default.DarkMode,
                            contentDescription = if (colors.isDark) "حالت روز" else "حالت شب",
                            tint = if (colors.isDark) Color(0xFFFBBF24) else Color(0xFF6366F1),
                            modifier = Modifier.size(headerIconSize)
                        )
                    }

                    // 4. QR Share Button
                    Box(
                        modifier = Modifier
                            .size(headerBtnSize)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .clickable { onShareClick() },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.QrCode2,
                            contentDescription = "اشتراک‌گذاری با بارکد QR",
                            tint = colors.skyBlue,
                            modifier = Modifier.size(headerIconSize)
                        )
                    }

                    // 5. Telegram Profile & Version Sculpted Pill (Right side)
                    Row(
                        modifier = Modifier
                            .weight(1f)
                            .height(headerBtnSize)
                            .luxuryCushion(shape = RoundedCornerShape(16.dp), elevation = 3.dp)
                            .clickable { onCheckUpdate() }
                            .padding(horizontal = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(5.dp),
                            modifier = Modifier.weight(1f, fill = false)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 20.dp else 24.dp)
                                    .clip(CircleShape)
                                    .background(
                                        Brush.radialGradient(
                                            listOf(Color(0xFFBAE6FD), Color(0xFF38BDF8), Color(0xFF0284C7))
                                        )
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Person,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(if (isSmallScreen) 11.dp else 14.dp)
                                )
                            }
                            Text(
                                text = userName,
                                fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = colors.textPrimary,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis
                            )
                        }

                        if (newVersionAvailable != null) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(6.dp))
                                    .background(Color(0xFFEF4444))
                                    .padding(horizontal = 5.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = "آپدیت",
                                    fontSize = 9.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                            }
                        } else {
                            Text(
                                text = "v$appVersion",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = colors.textSecondary
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(sectionSpacing))

                // ==================== 1. FULL SUBSCRIPTION ID / CODE BAR ====================
                val displayPin = if (userPin.isNotBlank()) userPin else (prefs.savedPin ?: "---")
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                        .padding(horizontal = if (isSmallScreen) 10.dp else 12.dp, vertical = if (isSmallScreen) 4.dp else 6.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        // Left actions: Copy & Share
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            // Share button
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 26.dp else 30.dp)
                                    .luxuryWell(shape = RoundedCornerShape(8.dp))
                                    .clickable {
                                        try {
                                            val sendIntent = Intent(Intent.ACTION_SEND).apply {
                                                putExtra(Intent.EXTRA_TEXT, "کد اشتراک من در آسان وی‌پی‌ان:\n$displayPin")
                                                type = "text/plain"
                                            }
                                            val shareIntent = Intent.createChooser(sendIntent, "اشتراک‌گذاری کد اشتراک")
                                            shareIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                            context.startActivity(shareIntent)
                                        } catch (e: Exception) {
                                            Toast.makeText(context, "خطا در اشتراک‌گذاری", Toast.LENGTH_SHORT).show()
                                        }
                                    },
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Share,
                                    contentDescription = "اشتراک‌گذاری کد",
                                    tint = colors.skyBlue,
                                    modifier = Modifier.size(16.dp)
                                )
                            }

                            // Copy button
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 26.dp else 30.dp)
                                    .luxuryWell(shape = RoundedCornerShape(8.dp))
                                    .clickable {
                                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                        clipboard.setPrimaryClip(ClipData.newPlainText("AsanVPN PIN", displayPin))
                                        Toast.makeText(context, "کد اشتراک کپی شد: $displayPin", Toast.LENGTH_SHORT).show()
                                    },
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.ContentCopy,
                                    contentDescription = "کپی کد اشتراک",
                                    tint = colors.jadeGreen,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                        }

                        // Right side: Label & Full Code
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                text = displayPin,
                                fontSize = if (isSmallScreen) 12.5.sp else 13.5.sp,
                                fontWeight = FontWeight.ExtraBold,
                                fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                                color = colors.textPrimary,
                                letterSpacing = 1.sp
                            )
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Text(
                                    text = "کد اشتراک:",
                                    fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textSecondary
                                )
                                Icon(
                                    imageVector = Icons.Default.Key,
                                    contentDescription = null,
                                    tint = colors.amberWarning,
                                    modifier = Modifier.size(14.dp)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(sectionSpacing))

                // ==================== 2. COMPACT DUAL METRIC CUSHIONS ====================
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(if (isSmallScreen) 6.dp else 8.dp)
                ) {
                    // Right Card (In RTL): حجم اشتراک
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .wrapContentHeight()
                            .defaultMinSize(minHeight = if (isSmallScreen) 44.dp else 50.dp)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .padding(horizontal = if (isSmallScreen) 8.dp else 10.dp, vertical = if (isSmallScreen) 4.dp else 6.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(
                                horizontalAlignment = Alignment.End,
                                verticalArrangement = Arrangement.Center,
                                modifier = Modifier.weight(1f).padding(end = 5.dp)
                            ) {
                                Text(
                                    text = "حجم اشتراک",
                                    fontSize = if (isSmallScreen) 9.sp else 10.sp,
                                    lineHeight = if (isSmallScreen) 11.sp else 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textSecondary
                                )
                                Text(
                                    text = if (isTrafficUnlimited) "نامحدود" else formatTrafficRemaining(trafficRemainingBytes),
                                    fontSize = if (isSmallScreen) 13.sp else 14.5.sp,
                                    lineHeight = if (isSmallScreen) 16.sp else 18.sp,
                                    fontWeight = FontWeight.Black,
                                    color = when {
                                        isExhaustedRemaining -> colors.coralRed
                                        isLowRemaining -> colors.amberWarning
                                        else -> colors.textPrimary
                                    },
                                    maxLines = 1
                                )
                            }
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 26.dp else 32.dp)
                                    .luxuryWell(shape = RoundedCornerShape(8.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                Canvas(modifier = Modifier.size(if (isSmallScreen) 15.dp else 18.dp)) {
                                    drawCircle(
                                        color = colors.jadeGreen.copy(alpha = 0.22f),
                                        radius = size.minDimension / 2,
                                        style = Stroke(width = 2.4.dp.toPx())
                                    )
                                    drawArc(
                                        color = if (isExhaustedRemaining) colors.coralRed else colors.jadeGreen,
                                        startAngle = -90f,
                                        sweepAngle = if (isTrafficUnlimited) 360f else 280f,
                                        useCenter = false,
                                        style = Stroke(width = 2.4.dp.toPx(), cap = StrokeCap.Round)
                                    )
                                }
                            }
                        }
                    }

                    // Left Card (In RTL): اعتبار زمانی
                    val isUnlimitedDays = daysLeft < 0
                    val isCriticalDays = !isUnlimitedDays && daysLeft in 0..3

                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .wrapContentHeight()
                            .defaultMinSize(minHeight = if (isSmallScreen) 44.dp else 50.dp)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .padding(horizontal = if (isSmallScreen) 8.dp else 10.dp, vertical = if (isSmallScreen) 4.dp else 6.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(
                                horizontalAlignment = Alignment.End,
                                verticalArrangement = Arrangement.Center,
                                modifier = Modifier.weight(1f).padding(end = 5.dp)
                            ) {
                                Text(
                                    text = "اعتبار زمانی",
                                    fontSize = if (isSmallScreen) 9.sp else 10.sp,
                                    lineHeight = if (isSmallScreen) 11.sp else 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textSecondary
                                )
                                Text(
                                    text = when {
                                        isUnlimitedDays -> "نامحدود"
                                        daysLeft == 0 -> "پایان امروز"
                                        else -> "$daysLeft روز"
                                    },
                                    fontSize = if (isSmallScreen) 13.sp else 14.5.sp,
                                    lineHeight = if (isSmallScreen) 16.sp else 18.sp,
                                    fontWeight = FontWeight.Black,
                                    color = if (isCriticalDays) colors.coralRed else colors.textPrimary,
                                    maxLines = 1
                                )
                            }
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 26.dp else 32.dp)
                                    .luxuryWell(shape = RoundedCornerShape(8.dp)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Schedule,
                                    contentDescription = null,
                                    tint = if (isCriticalDays) colors.coralRed else colors.skyBlue,
                                    modifier = Modifier.size(if (isSmallScreen) 15.dp else 18.dp)
                                )
                            }
                        }
                    }
                }

                // ==================== LOW TRAFFIC WARNING BANNER ====================
                if (isLowRemaining || isExhaustedRemaining) {
                    Spacer(modifier = Modifier.height(10.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .luxuryCushion(shape = RoundedCornerShape(18.dp), elevation = 4.dp)
                            .border(
                                1.dp,
                                if (isExhaustedRemaining) colors.coralRed.copy(alpha = 0.5f) else colors.amberWarning.copy(alpha = 0.5f),
                                RoundedCornerShape(18.dp)
                            )
                            .padding(horizontal = 14.dp, vertical = 10.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .clip(CircleShape)
                                    .background(
                                        if (isExhaustedRemaining) colors.coralRed.copy(alpha = 0.15f) else colors.amberWarning.copy(alpha = 0.15f)
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Warning,
                                    contentDescription = "هشدار حجم",
                                    tint = if (isExhaustedRemaining) colors.coralRed else colors.amberWarning,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                            Column(
                                modifier = Modifier.weight(1f),
                                horizontalAlignment = Alignment.End
                            ) {
                                Text(
                                    text = if (isExhaustedRemaining)
                                        "⚠️ حجم اشتراک شما به پایان رسیده است!"
                                    else
                                        "⚠️ حجم رو به پایان است: (${formatTrafficRemaining(trafficRemainingBytes)})",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isExhaustedRemaining) colors.coralRed else colors.amberWarning,
                                    textAlign = TextAlign.Right
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = "جهت جلوگیری از قطع ارتباط، نسبت به تمدید اقدام فرمایید.",
                                    fontSize = 11.sp,
                                    color = colors.textSecondary,
                                    textAlign = TextAlign.Right
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(sectionSpacing))

                // ==================== 3. SERVER SELECTOR CARD WITH AUTO SWITCH ====================
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(shape = RoundedCornerShape(16.dp), elevation = 3.dp)
                        .clickable { showServerSelectDialog = true }
                        .padding(horizontal = if (isSmallScreen) 10.dp else 12.dp, vertical = if (isSmallScreen) 6.dp else 8.dp)
                ) {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Ping Badge & Dropdown Chevron on Left
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .luxuryWell(shape = RoundedCornerShape(12.dp))
                                        .padding(horizontal = if (isSmallScreen) 6.dp else 8.dp, vertical = if (isSmallScreen) 3.dp else 5.dp)
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(5.dp)
                                    ) {
                                        Box(
                                            modifier = Modifier
                                                .size(7.dp)
                                                .clip(CircleShape)
                                                .background(if (isConnected) colors.jadeGreen else colors.textMuted)
                                        )
                                        Text(
                                            text = "$serverPing ms",
                                            fontSize = 11.5.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = if (isConnected) colors.jadeGreen else colors.textSecondary
                                        )
                                    }
                                }

                                // Dropdown chevron indicator
                                Box(
                                    modifier = Modifier
                                        .size(if (isSmallScreen) 22.dp else 26.dp)
                                        .luxuryWell(shape = CircleShape),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.ExpandMore,
                                        contentDescription = "لیست سرورها",
                                        tint = colors.textSecondary,
                                        modifier = Modifier.size(if (isSmallScreen) 14.dp else 17.dp)
                                    )
                                }
                            }

                            // Server Remark on Right
                            Column(
                                horizontalAlignment = Alignment.End,
                                modifier = Modifier.weight(1f).padding(start = 10.dp)
                            ) {
                                Text(
                                    text = serverRemark,
                                    fontSize = if (isSmallScreen) 11.sp else 12.5.sp,
                                    fontWeight = FontWeight.ExtraBold,
                                    color = colors.textPrimary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    textAlign = TextAlign.Right
                                )
                                Spacer(modifier = Modifier.height(3.dp))
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(5.dp)
                                ) {
                                    Text(
                                        text = if (isAutoServerMode) "انتخاب هوشمند فعال" else "انتخاب دستی",
                                        fontSize = if (isSmallScreen) 9.sp else 10.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = if (isAutoServerMode) colors.jadeGreen else colors.amberWarning
                                    )
                                    Box(
                                        modifier = Modifier
                                            .size(6.dp)
                                            .clip(CircleShape)
                                            .background(if (isAutoServerMode) colors.jadeGreen else colors.amberWarning)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(if (isSmallScreen) 3.dp else 6.dp))

                        // Bottom row: Auto switch & sleek server count chip (never wraps!)
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Auto Mode Switch Chip
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(if (isSmallScreen) 4.dp else 6.dp),
                                modifier = Modifier
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(
                                        if (isAutoServerMode) colors.jadeGreen.copy(alpha = 0.12f)
                                        else colors.textMuted.copy(alpha = 0.1f)
                                    )
                                    .clickable {
                                        onToggleAutoServerMode(!isAutoServerMode)
                                    }
                                    .padding(horizontal = if (isSmallScreen) 6.dp else 8.dp, vertical = if (isSmallScreen) 2.dp else 4.dp)
                            ) {
                                Switch(
                                    checked = isAutoServerMode,
                                    onCheckedChange = { onToggleAutoServerMode(it) },
                                    modifier = Modifier.scale(if (isSmallScreen) 0.58f else 0.70f),
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = Color.White,
                                        checkedTrackColor = colors.jadeGreen,
                                        uncheckedThumbColor = Color.White,
                                        uncheckedTrackColor = colors.textMuted.copy(alpha = 0.4f)
                                    )
                                )
                                Text(
                                    text = if (isAutoServerMode) "حالت خودکار" else "حالت دستی",
                                    fontSize = if (isSmallScreen) 9.sp else 10.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isAutoServerMode) colors.jadeGreen else colors.textSecondary
                                )
                            }

                            // Compact Server List Chip
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(3.dp),
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(if (colors.isDark) Color(0x22FFFFFF) else Color(0x12000000))
                                    .padding(horizontal = if (isSmallScreen) 6.dp else 8.dp, vertical = if (isSmallScreen) 3.dp else 4.dp)
                            ) {
                                Text(
                                    text = "${availableNodes.size.coerceAtLeast(1)} سرور",
                                    fontSize = if (isSmallScreen) 9.sp else 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textSecondary
                                )
                                Icon(
                                    imageVector = Icons.Default.SwapVert,
                                    contentDescription = "تغییر سرور",
                                    tint = colors.textSecondary,
                                    modifier = Modifier.size(if (isSmallScreen) 12.dp else 14.dp)
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(orbVerticalSpacing))

            // ==================== CENTERPIECE: 3D POWER ORB ====================
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(
                    modifier = Modifier
                        .size(orbTotalSize)
                        .clip(CircleShape)
                        .clickable(
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null
                        ) {
                            onToggleConnect()
                        },
                    contentAlignment = Alignment.Center
                ) {
                    // 1. Breathing Subsurface Aura
                    Box(
                        modifier = Modifier
                            .size(auraSize)
                            .scale(if (isConnecting) pulseScale else if (isConnected) 1.02f else 1f)
                            .clip(CircleShape)
                            .background(
                                Brush.radialGradient(
                                    colors = listOf(
                                        when {
                                            isConnected -> colors.jadeGlow
                                            isConnecting -> colors.amberGlow
                                            else -> colors.cushionShadowAmbient.copy(alpha = 0.25f)
                                        },
                                        Color.Transparent
                                    )
                                )
                            )
                    )

                    // 2. Outer Smooth Torus Cushion Ring
                    Box(
                        modifier = Modifier
                            .size(torusSize)
                            .shadow(
                                elevation = if (isConnected) 12.dp else 8.dp,
                                shape = CircleShape,
                                ambientColor = colors.torusShadow,
                                spotColor = colors.torusShadow
                            )
                            .background(colors.torusOuterBrush, CircleShape)
                            .border(
                                width = 1.5.dp,
                                brush = Brush.linearGradient(
                                    colors = if (colors.isDark) {
                                        listOf(Color.White.copy(alpha = 0.2f), Color.Transparent)
                                    } else {
                                        listOf(Color.White, Color(0xFFCBD5E1).copy(alpha = 0.4f))
                                    }
                                ),
                                shape = CircleShape
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        // 3. Translucent Liquid Jade / Amber / Slate Glass Halo Channel
                        val channelGradient = when {
                            isConnected -> {
                                if (colors.isDark) {
                                    Brush.radialGradient(listOf(Color(0xFF34D399), Color(0x6610B981), Color(0x88064E3B)))
                                } else {
                                    Brush.radialGradient(listOf(Color(0xFFA7F3D0), Color(0x7710B981), Color(0x99059669)))
                                }
                            }
                            isConnecting -> {
                                if (colors.isDark) {
                                    Brush.radialGradient(listOf(Color(0xFFFBBF24), Color(0x66F59E0B), Color(0x8892400E)))
                                } else {
                                    Brush.radialGradient(listOf(Color(0xFFFDE68A), Color(0x77F59E0B), Color(0x99D97706)))
                                }
                            }
                            else -> {
                                if (colors.isDark) {
                                    Brush.radialGradient(listOf(Color(0xFF1E293B), Color(0x66334155), Color(0x880F172A)))
                                } else {
                                    Brush.radialGradient(listOf(Color(0xFFE2E8F0), Color(0x6694A3B8), Color(0x8864748B)))
                                }
                            }
                        }

                        Box(
                            modifier = Modifier
                                .size(haloSize)
                                .clip(CircleShape)
                                .background(channelGradient)
                                .border(
                                    width = 1.dp,
                                    color = if (isConnected) colors.jadeGreen.copy(alpha = 0.4f) else Color.Transparent,
                                    shape = CircleShape
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            // Rotating Silk Light Sheen
                            if (isConnected || isConnecting) {
                                Box(
                                    modifier = Modifier
                                        .size(haloSize)
                                        .rotate(silkSheenRotation)
                                        .background(
                                            Brush.sweepGradient(
                                                colors = listOf(
                                                    Color.Transparent,
                                                    Color.White.copy(alpha = if (colors.isDark) 0.35f else 0.6f),
                                                    Color.Transparent,
                                                    if (isConnected) colors.jadeGreen.copy(alpha = 0.3f) else colors.amberWarning.copy(alpha = 0.3f),
                                                    Color.Transparent
                                                )
                                            ),
                                            CircleShape
                                        )
                                )
                            }

                            // 4. Domed Tactile 3D Pebble Button Cap
                            val pebbleBrush = when {
                                isConnected -> colors.pebbleCapBrushConnected
                                isConnecting -> colors.pebbleCapBrushConnecting
                                else -> colors.pebbleCapBrushDisconnected
                            }

                            Box(
                                modifier = Modifier
                                    .size(capSize)
                                    .shadow(
                                        elevation = 8.dp,
                                        shape = CircleShape,
                                        ambientColor = colors.cushionShadowAmbient,
                                        spotColor = colors.cushionShadowSpot
                                    )
                                    .background(pebbleBrush, CircleShape)
                                    .border(
                                        width = if (isConnected || isConnecting) 2.5.dp else 1.5.dp,
                                        color = when {
                                            isConnected -> colors.jadeGreen.copy(alpha = 0.8f)
                                            isConnecting -> colors.amberWarning.copy(alpha = 0.8f)
                                            else -> if (colors.isDark) Color.White.copy(alpha = 0.15f) else Color.White
                                        },
                                        shape = CircleShape
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                // Top Specular Liquid Glass Dome Reflection
                                Box(
                                    modifier = Modifier
                                        .align(Alignment.TopCenter)
                                        .padding(top = 6.dp)
                                        .size(width = capSize * 0.62f, height = capSize * 0.25f)
                                        .clip(CircleShape)
                                        .background(colors.domeGlossBrush)
                                )

                                // Power Glyph Symbol
                                Icon(
                                    imageVector = Icons.Default.PowerSettingsNew,
                                    contentDescription = "اتصال وی‌پی‌ان",
                                    tint = when {
                                        isConnected -> colors.jadeGreen
                                        isConnecting -> colors.amberWarning
                                        else -> if (colors.isDark) Color(0xFF64748B) else Color(0xFF94A3B8)
                                    },
                                    modifier = Modifier.size(powerIconSize)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(if (isSmallScreen) 4.dp else 8.dp))

                // Status Title & Subtitle
                Text(
                    text = statusBadgeText,
                    fontSize = if (isSmallScreen) 14.5.sp else 17.5.sp,
                    fontWeight = FontWeight.Black,
                    color = statusTitleColor,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(3.dp))

                Text(
                    text = if (isSmallScreen && !isConnected && !isConnecting) "جهت برقراری اتصال دکمه را لمس کنید" else statusSubText,
                    fontSize = if (isSmallScreen) 9.sp else 10.5.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = colors.textSecondary,
                    textAlign = TextAlign.Center,
                    maxLines = 1
                )

                // Floating Duration Pill
                AnimatedVisibility(visible = isConnected) {
                    Box(
                        modifier = Modifier
                            .padding(top = if (isSmallScreen) 3.dp else 6.dp)
                            .luxuryWell(shape = RoundedCornerShape(14.dp))
                            .padding(horizontal = if (isSmallScreen) 10.dp else 12.dp, vertical = if (isSmallScreen) 3.dp else 4.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Text(
                                text = "مدت اتصال: ${formatDuration(connectedSeconds)}",
                                fontSize = if (isSmallScreen) 10.5.sp else 11.5.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = colors.textPrimary
                            )
                            Box(
                                modifier = Modifier
                                    .size(20.dp)
                                    .clip(CircleShape)
                                    .background(
                                        Brush.radialGradient(
                                            listOf(Color(0xFFA7F3D0), Color(0xFF10B981), Color(0xFF059669))
                                        )
                                    ),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Timer,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(12.dp)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(if (isSmallScreen) 4.dp else 8.dp))

                // ==================== LIVE TRAFFIC CAPSULE (Directly under timer) ====================
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                        .padding(horizontal = if (isSmallScreen) 12.dp else 14.dp, vertical = if (isSmallScreen) 4.dp else 7.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // IN (دریافت)
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 24.dp else 30.dp)
                                    .luxuryWell(shape = CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.ArrowDownward,
                                    contentDescription = "دریافت",
                                    tint = colors.skyBlue,
                                    modifier = Modifier.size(if (isSmallScreen) 13.dp else 16.dp)
                                )
                            }
                            Column {
                                Text(
                                    text = "دریافت (In)",
                                    fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textSecondary
                                )
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = downloadTraffic,
                                        fontSize = if (isSmallScreen) 11.5.sp else 12.5.sp,
                                        fontWeight = FontWeight.ExtraBold,
                                        color = colors.textPrimary
                                    )
                                    if (downloadSpeed.isNotBlank()) {
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(
                                            text = downloadSpeed,
                                            fontSize = 9.5.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = colors.skyBlue
                                        )
                                    }
                                }
                            }
                        }

                        // Soft Vertical Divider
                        Box(
                            modifier = Modifier
                                .height(if (isSmallScreen) 18.dp else 24.dp)
                                .width(1.dp)
                                .background(colors.dividerSoft)
                        )

                        // OUT (ارسال)
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(if (isSmallScreen) 24.dp else 30.dp)
                                    .luxuryWell(shape = CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.ArrowUpward,
                                    contentDescription = "ارسال",
                                    tint = colors.jadeGreen,
                                    modifier = Modifier.size(if (isSmallScreen) 13.dp else 16.dp)
                                )
                            }
                            Column {
                                Text(
                                    text = "ارسال (Out)",
                                    fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textSecondary
                                )
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = uploadTraffic,
                                        fontSize = if (isSmallScreen) 11.5.sp else 12.5.sp,
                                        fontWeight = FontWeight.ExtraBold,
                                        color = colors.textPrimary
                                    )
                                    if (uploadSpeed.isNotBlank()) {
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(
                                            text = uploadSpeed,
                                            fontSize = 9.5.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = colors.jadeGreen
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(if (isSmallScreen) 4.dp else 8.dp))

            // ==================== BOTTOM SECTION ====================
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(if (isSmallScreen) 4.dp else 6.dp)
            ) {
                // 1. Direct Iranian Routing Pill
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 2.dp)
                        .padding(horizontal = if (isSmallScreen) 10.dp else 12.dp, vertical = if (isSmallScreen) 4.dp else 6.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.Center
                    ) {
                        Text(
                            text = "بانک‌ها و سایت‌های ایرانی مستقیم باز می‌شوند",
                            fontSize = if (isSmallScreen) 9.5.sp else 11.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = colors.textPrimary,
                            textAlign = TextAlign.Center
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        // Glossy 3D Iranian Flag Pebble
                        Box(
                            modifier = Modifier
                                .size(width = if (isSmallScreen) 20.dp else 24.dp, height = if (isSmallScreen) 12.dp else 15.dp)
                                .clip(RoundedCornerShape(3.dp))
                                .border(0.5.dp, Color.White.copy(alpha = 0.5f), RoundedCornerShape(3.dp))
                        ) {
                            Column(modifier = Modifier.fillMaxSize()) {
                                Box(modifier = Modifier.weight(1f).fillMaxWidth().background(IranFlagGreen))
                                Box(modifier = Modifier.weight(1f).fillMaxWidth().background(IranFlagWhite), contentAlignment = Alignment.Center) {
                                    Box(modifier = Modifier.size(3.dp).clip(CircleShape).background(IranFlagRed))
                                }
                                Box(modifier = Modifier.weight(1f).fillMaxWidth().background(IranFlagRed))
                            }
                        }
                    }
                }

                // 2. Dual Action Row: Support Bot & Purchase Bot
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(if (isSmallScreen) 6.dp else 8.dp)
                ) {
                    // Button 1: ارتباط با پشتیبانی (Support Bot)
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(if (isSmallScreen) 34.dp else 40.dp)
                            .luxuryCushion(shape = RoundedCornerShape(14.dp), elevation = 3.dp)
                            .clickable {
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/Asanvpnsupport_bot"))
                                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    Toast.makeText(context, "تلگرام یافت نشد: t.me/Asanvpnsupport_bot", Toast.LENGTH_SHORT).show()
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.SupportAgent,
                                contentDescription = null,
                                tint = colors.skyBlue,
                                modifier = Modifier.size(if (isSmallScreen) 14.dp else 17.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "ارتباط با پشتیبانی",
                                fontSize = if (isSmallScreen) 9.5.sp else 11.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = colors.textPrimary
                            )
                        }
                    }

                    // Button 2: خرید یا تمدید (Purchase / Renewal Bot)
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(if (isSmallScreen) 34.dp else 40.dp)
                            .shadow(
                                elevation = 4.dp,
                                shape = RoundedCornerShape(18.dp),
                                ambientColor = colors.coralRed.copy(alpha = 0.2f),
                                spotColor = colors.coralRed.copy(alpha = 0.2f)
                            )
                            .background(colors.coralCtaBrush, RoundedCornerShape(18.dp))
                            .border(1.dp, colors.coralCtaBorder, RoundedCornerShape(18.dp))
                            .clickable {
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/asan_vpn_p_bot"))
                                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    Toast.makeText(context, "تلگرام یافت نشد: t.me/asan_vpn_p_bot", Toast.LENGTH_SHORT).show()
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.ShoppingCart,
                                contentDescription = null,
                                tint = colors.coralCtaText,
                                modifier = Modifier.size(if (isSmallScreen) 13.dp else 16.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "خرید یا تمدید",
                                fontSize = if (isSmallScreen) 9.5.sp else 11.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color = colors.coralCtaText
                            )
                        }
                    }
                }

                // 3. Switch PIN & Footer Version
                TextButton(
                    onClick = onChangePin,
                    modifier = Modifier.padding(top = 0.dp),
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(5.dp)
                    ) {
                        Text(
                            text = "ورود با کد اشتراک دیگر",
                            fontSize = if (isSmallScreen) 9.5.sp else 11.5.sp,
                            fontWeight = FontWeight.Bold,
                            color = colors.textSecondary
                        )
                        Icon(
                            imageVector = Icons.Default.Key,
                            contentDescription = null,
                            tint = colors.textSecondary,
                            modifier = Modifier.size(15.dp)
                        )
                    }
                }

                Text(
                    text = "نسخه $appVersion • سامانه ابری آسان وی‌پی‌ان",
                    fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                    fontWeight = FontWeight.Medium,
                    color = colors.textMuted
                )
            }
        }
    }

    // Server Selection Dialog (for choosing from 200+ links with search and Auto mode toggle)
    if (showServerSelectDialog) {
        ServerSelectionDialog(
            availableNodes = availableNodes,
            currentSelectedRemark = serverRemark,
            isAutoServerMode = isAutoServerMode,
            onDismiss = { showServerSelectDialog = false },
            onSelectAuto = {
                onToggleAutoServerMode(true)
                showServerSelectDialog = false
            },
            onSelectNode = { selectedNode ->
                onSelectServerNode(selectedNode)
                showServerSelectDialog = false
            }
        )
    }

    // Debug Report Dialog
    if (showDebugDialog) {
        val currentLogText = if (isAdminMode) AppLogger.getAdminLog() else AppLogger.getUserLog()
        AlertDialog(
            onDismissRequest = { showDebugDialog = false },
            title = {
                Text(
                    text = "گزارش وضعیت و عیب‌یابی",
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    color = colors.textPrimary
                )
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = currentLogText,
                        fontSize = 11.sp,
                        fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                        color = colors.textSecondary
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("AsanVPN Diagnostics", currentLogText))
                        Toast.makeText(context, "گزارش در حافظه کپی شد", Toast.LENGTH_SHORT).show()
                        showDebugDialog = false
                    }
                ) {
                    Text("کپی گزارش", color = colors.jadeGreen, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDebugDialog = false }) {
                    Text("بستن", color = colors.textSecondary)
                }
            }
        )
    }

    // App Filter & Whitelist Dialog (Opened via Gear button)
    if (showAppFilterDialog) {
        AppFilterDialog(
            initialEnabled = isAppFilterEnabled,
            initialWhitelist = appFilterWhitelist,
            initialSpeedOptEnabled = isSpeedOptimizationEnabled,
            initialGeminiOptEnabled = isGeminiOptimizationEnabled,
            initialVoiceCallOptEnabled = isVoiceCallOptimizationEnabled,
            isVpnConnected = isConnected,
            onDismiss = { showAppFilterDialog = false },
            onSave = { enabled, whitelist, speedOpt, geminiOpt, voiceCallOpt ->
                isAppFilterEnabled = enabled
                appFilterWhitelist = whitelist
                isSpeedOptimizationEnabled = speedOpt
                isGeminiOptimizationEnabled = geminiOpt
                isVoiceCallOptimizationEnabled = voiceCallOpt
                onSaveAppFilter(enabled, whitelist, speedOpt, geminiOpt, voiceCallOpt)
            }
        )
    }
}
