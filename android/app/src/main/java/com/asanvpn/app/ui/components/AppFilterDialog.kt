package com.asanvpn.app.ui.components

import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.asanvpn.app.ui.theme.LuxuryTheme
import com.asanvpn.app.ui.theme.luxuryCushion
import com.asanvpn.app.ui.theme.luxuryWell
import com.asanvpn.app.service.PingTester
import com.asanvpn.app.util.AppFilterHelper
import com.asanvpn.app.data.PreferencesManager
import com.asanvpn.app.data.VpnRepository
import com.asanvpn.app.data.models.VpnNode
import com.asanvpn.app.util.AppFilterItem
import kotlinx.coroutines.launch

@Composable
fun AppFilterDialog(
    initialEnabled: Boolean,
    initialWhitelist: Set<String>,
    initialSpeedOptEnabled: Boolean = false,
    initialGeminiOptEnabled: Boolean = false,
    initialVoiceCallOptEnabled: Boolean = false,
    isVpnConnected: Boolean,
    onDismiss: () -> Unit,
    onSave: (enabled: Boolean, whitelist: Set<String>, speedOptEnabled: Boolean, geminiOptEnabled: Boolean, voiceCallOptEnabled: Boolean) -> Unit
) {
    val context = LocalContext.current
    val colors = LuxuryTheme.colors
    val coroutineScope = rememberCoroutineScope()

    val configuration = LocalConfiguration.current
    val screenHeight = configuration.screenHeightDp.dp
    val screenWidth = configuration.screenWidthDp.dp
    val isSmallScreen = screenHeight < 680.dp || screenWidth <= 365.dp

    var isEnabled by remember { mutableStateOf(initialEnabled) }
    var isSpeedOptEnabled by remember { mutableStateOf(initialSpeedOptEnabled) }
    var isGeminiOptEnabled by remember { mutableStateOf(initialGeminiOptEnabled) }
    var isVoiceCallOptEnabled by remember { mutableStateOf(initialVoiceCallOptEnabled) }
    var isGeminiTesting by remember { mutableStateOf(false) }
    var geminiTestStatus by remember { mutableStateOf<String?>(null) }
    var isUdpTesting by remember { mutableStateOf(false) }
    var udpTestStatus by remember { mutableStateOf<String?>(null) }
    val selectedPackages = remember { mutableStateListOf<String>().apply { addAll(initialWhitelist) } }

    var searchQuery by remember { mutableStateOf("") }
    var installedApps by remember { mutableStateOf<List<AppFilterItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        isLoading = true
        val apps = AppFilterHelper.loadInstalledApps(context)
        installedApps = apps
        isLoading = false
    }

    val filteredApps = remember(installedApps, searchQuery) {
        if (searchQuery.isBlank()) {
            installedApps
        } else {
            val q = searchQuery.trim().lowercase()
            installedApps.filter {
                it.name.lowercase().contains(q) || it.packageName.lowercase().contains(q)
            }
        }
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            dismissOnBackPress = true,
            dismissOnClickOutside = true
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(if (isSmallScreen) 0.98f else 0.94f)
                .fillMaxHeight(if (isSmallScreen) 0.95f else 0.88f)
                .luxuryCushion(
                    shape = RoundedCornerShape(if (isSmallScreen) 22.dp else 28.dp),
                    elevation = 12.dp
                )
                .padding(if (isSmallScreen) 12.dp else 20.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // ==================== 1. FIXED HEADER (ALWAYS VISIBLE AT TOP) ====================
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
                        modifier = Modifier
                            .weight(1f)
                            .padding(horizontal = 4.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Tune,
                                contentDescription = null,
                                tint = colors.jadeGreen,
                                modifier = Modifier.size(if (isSmallScreen) 17.dp else 20.dp)
                            )
                            Text(
                                text = if (isSmallScreen) "تنظیمات و فیلتر برنامه‌ها" else "فیلتر برنامه‌ها و بهینه‌سازی (App Filter)",
                                fontSize = if (isSmallScreen) 14.sp else 16.5.sp,
                                fontWeight = FontWeight.Black,
                                color = colors.textPrimary,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                textAlign = TextAlign.Center
                            )
                        }
                        Text(
                            text = "انتخاب برنامه‌های مجاز جهت عبور از فیلترشکن",
                            fontSize = if (isSmallScreen) 10.sp else 11.5.sp,
                            color = colors.textSecondary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            textAlign = TextAlign.Center
                        )
                    }

                    Box(
                        modifier = Modifier
                            .size(if (isSmallScreen) 32.dp else 36.dp)
                            .luxuryCushion(shape = CircleShape, elevation = 2.dp)
                            .clickable {
                                // Select popular apps with 1 click
                                val popularInstalled = installedApps
                                    .filter { it.packageName in AppFilterHelper.POPULAR_PACKAGES }
                                    .map { it.packageName }
                                var addedCount = 0
                                for (pkg in popularInstalled) {
                                    if (!selectedPackages.contains(pkg)) {
                                        selectedPackages.add(pkg)
                                        addedCount++
                                    }
                                }
                                if (!isEnabled) isEnabled = true
                                Toast.makeText(
                                    context,
                                    "برنامه‌های محبوب انتخاب شدند (${popularInstalled.size} برنامه)",
                                    Toast.LENGTH_SHORT
                                ).show()
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = "برنامه‌های محبوب",
                            tint = Color(0xFFF59E0B),
                            modifier = Modifier.size(if (isSmallScreen) 16.dp else 18.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(if (isSmallScreen) 8.dp else 12.dp))

                // ==================== 2. SCROLLABLE BODY (WEIGHT 1F) ====================
                // Everything scrolls smoothly in a single LazyColumn so the Save/Cancel buttons
                // are ALWAYS pinned at the bottom and never clipped, even on Galaxy A5!
                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(if (isSmallScreen) 8.dp else 10.dp)
                ) {
                    // ITEM: MASTER SWITCH CARD (WHITELIST)
                    item(key = "whitelist_card") {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryCushion(
                                    shape = RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp),
                                    elevation = 4.dp
                                )
                                .border(
                                    1.dp,
                                    if (isEnabled) colors.jadeGreen.copy(alpha = 0.4f) else Color.Transparent,
                                    RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp)
                                )
                                .clickable { isEnabled = !isEnabled }
                                .padding(
                                    horizontal = if (isSmallScreen) 12.dp else 14.dp,
                                    vertical = if (isSmallScreen) 8.dp else 12.dp
                                )
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Switch(
                                    checked = isEnabled,
                                    onCheckedChange = { isEnabled = it },
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = Color.White,
                                        checkedTrackColor = colors.jadeGreen,
                                        uncheckedThumbColor = colors.textSecondary,
                                        uncheckedTrackColor = if (colors.isDark) Color(0xFF1E293B) else Color(0xFFCBD5E1)
                                    )
                                )

                                Column(
                                    modifier = Modifier
                                        .weight(1f)
                                        .padding(end = 10.dp),
                                    horizontalAlignment = Alignment.End
                                ) {
                                    Text(
                                        text = "حالت لیست سفید (Whitelist)",
                                        fontSize = if (isSmallScreen) 12.5.sp else 13.5.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = colors.textPrimary,
                                        textAlign = TextAlign.Right
                                    )
                                    Text(
                                        text = if (isEnabled)
                                            "فقط برنامه‌های تیک‌خورده (${selectedPackages.size} برنامه) از فیلترشکن رد می‌شوند"
                                        else
                                            "غیرفعال: تمام ترافیک دستگاه از فیلترشکن عبور می‌کند",
                                        fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                        color = if (isEnabled) colors.jadeGreen else colors.textSecondary,
                                        textAlign = TextAlign.Right
                                    )
                                }
                            }
                        }
                    }

                    // ITEM: SPEED OPTIMIZATION CARD
                    item(key = "speed_opt_card") {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryCushion(
                                    shape = RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp),
                                    elevation = 4.dp
                                )
                                .border(
                                    1.dp,
                                    if (isSpeedOptEnabled) Color(0xFF38BDF8).copy(alpha = 0.4f) else Color.Transparent,
                                    RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp)
                                )
                                .clickable { isSpeedOptEnabled = !isSpeedOptEnabled }
                                .padding(
                                    horizontal = if (isSmallScreen) 12.dp else 14.dp,
                                    vertical = if (isSmallScreen) 8.dp else 12.dp
                                )
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Switch(
                                    checked = isSpeedOptEnabled,
                                    onCheckedChange = { isSpeedOptEnabled = it },
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = Color.White,
                                        checkedTrackColor = Color(0xFF0284C7),
                                        uncheckedThumbColor = colors.textSecondary,
                                        uncheckedTrackColor = if (colors.isDark) Color(0xFF1E293B) else Color(0xFFCBD5E1)
                                    )
                                )

                                Column(
                                    modifier = Modifier
                                        .weight(1f)
                                        .padding(end = 10.dp),
                                    horizontalAlignment = Alignment.End
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                                    ) {
                                        Text(
                                            text = "بهینه‌سازی هوشمند سرعت دانلود",
                                            fontSize = if (isSmallScreen) 12.5.sp else 13.5.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = colors.textPrimary,
                                            textAlign = TextAlign.Right
                                        )
                                        Icon(
                                            imageVector = Icons.Default.Speed,
                                            contentDescription = null,
                                            tint = Color(0xFF38BDF8),
                                            modifier = Modifier.size(15.dp)
                                        )
                                    }
                                    Text(
                                        text = if (isSpeedOptEnabled)
                                            "فعال: تست ۵ سرور برتر با دانلود ۴ مگابایت در پس‌زمینه و سوییچ خودکار به سریع‌ترین سرور"
                                        else
                                            "غیرفعال: اتصال طبق کمترین پینگ (صرفه‌جویی باتری و حجم)",
                                        fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                        color = if (isSpeedOptEnabled) Color(0xFF38BDF8) else colors.textSecondary,
                                        textAlign = TextAlign.Right
                                    )
                                }
                            }
                        }
                    }

                    // ITEM: GEMINI AI COMPATIBILITY CARD
                    item(key = "gemini_opt_card") {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryCushion(
                                    shape = RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp),
                                    elevation = 4.dp
                                )
                                .border(
                                    1.dp,
                                    if (isGeminiOptEnabled) Color(0xFFA855F7).copy(alpha = 0.5f) else Color.Transparent,
                                    RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp)
                                )
                                .padding(
                                    horizontal = if (isSmallScreen) 12.dp else 14.dp,
                                    vertical = if (isSmallScreen) 8.dp else 12.dp
                                )
                        ) {
                            Column(modifier = Modifier.fillMaxWidth()) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { isGeminiOptEnabled = !isGeminiOptEnabled },
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Switch(
                                        checked = isGeminiOptEnabled,
                                        onCheckedChange = { isGeminiOptEnabled = it },
                                        colors = SwitchDefaults.colors(
                                            checkedThumbColor = Color.White,
                                            checkedTrackColor = Color(0xFF9333EA),
                                            uncheckedThumbColor = colors.textSecondary,
                                            uncheckedTrackColor = if (colors.isDark) Color(0xFF1E293B) else Color(0xFFCBD5E1)
                                        )
                                    )

                                    Column(
                                        modifier = Modifier
                                            .weight(1f)
                                            .padding(end = 10.dp),
                                        horizontalAlignment = Alignment.End
                                    ) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            Text(
                                                text = "سازگاری اختصاصی هوش مصنوعی Gemini",
                                                fontSize = if (isSmallScreen) 12.5.sp else 13.5.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = colors.textPrimary,
                                                textAlign = TextAlign.Right
                                            )
                                            Icon(
                                                imageVector = Icons.Default.AutoAwesome,
                                                contentDescription = null,
                                                tint = Color(0xFFA855F7),
                                                modifier = Modifier.size(15.dp)
                                            )
                                        }
                                        Text(
                                            text = if (isGeminiOptEnabled)
                                                "فعال: اتصال انحصاری به سرورهای سازگار با گوگل جمینای بدون خطای تحریم و لوکیشن"
                                            else
                                                "غیرفعال: انتخاب معمولی سرورها طبق کمترین پینگ",
                                            fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                            color = if (isGeminiOptEnabled) Color(0xFFA855F7) else colors.textSecondary,
                                            textAlign = TextAlign.Right
                                        )
                                    }
                                }

                                // Live Gemini Connectivity Test Button
                                if (isVpnConnected) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    HorizontalDivider(
                                        color = colors.textSecondary.copy(alpha = 0.2f),
                                        thickness = 0.5.dp
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Button(
                                            onClick = {
                                                if (!isGeminiTesting) {
                                                    isGeminiTesting = true
                                                    geminiTestStatus = "در حال تست ارتباط با گوگل جمینای..."
                                                    coroutineScope.launch {
                                                        val prefs = PreferencesManager(context)
                                                        val activeRemark = prefs.selectedServerRemark
                                                        val activeNode = VpnRepository(context).getCachedNodes().firstOrNull { it.remark == activeRemark }
                                                        val res = PingTester.testLiveGeminiConnectivity(activeNode = activeNode)
                                                        isGeminiTesting = false
                                                        if (res.isSuccess) {
                                                            geminiTestStatus = "✅ ${res.message}"
                                                            if (activeNode != null) {
                                                                com.asanvpn.app.data.NodeMetricsCache.saveGeminiCompatibility(activeNode, true, res.latencyMs)
                                                            }
                                                        } else {
                                                            geminiTestStatus = "❌ ${res.message}"
                                                        }
                                                    }
                                                }
                                            },
                                            enabled = !isGeminiTesting,
                                            colors = ButtonDefaults.buttonColors(
                                                containerColor = Color(0xFF9333EA).copy(alpha = 0.15f),
                                                contentColor = Color(0xFFA855F7)
                                            ),
                                            shape = RoundedCornerShape(10.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                                        ) {
                                            if (isGeminiTesting) {
                                                CircularProgressIndicator(
                                                    modifier = Modifier.size(12.dp),
                                                    color = Color(0xFFA855F7),
                                                    strokeWidth = 2.dp
                                                )
                                                Spacer(modifier = Modifier.width(4.dp))
                                            }
                                            Text(
                                                text = if (isGeminiTesting) "در حال تست..." else "تست اتصال به Gemini",
                                                fontSize = 10.5.sp,
                                                fontWeight = FontWeight.Bold
                                            )
                                        }

                                        if (geminiTestStatus != null) {
                                            Text(
                                                text = geminiTestStatus ?: "",
                                                fontSize = 10.sp,
                                                color = if (geminiTestStatus?.startsWith("✅") == true) colors.jadeGreen else Color(0xFFEF4444),
                                                textAlign = TextAlign.Right,
                                                modifier = Modifier.weight(1f).padding(start = 6.dp),
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ITEM: VOICE CALL & CLUBHOUSE COMPATIBILITY CARD
                    item(key = "voice_call_opt_card") {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryCushion(
                                    shape = RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp),
                                    elevation = 4.dp
                                )
                                .border(
                                    1.dp,
                                    if (isVoiceCallOptEnabled) Color(0xFF10B981).copy(alpha = 0.5f) else Color.Transparent,
                                    RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp)
                                )
                                .padding(
                                    horizontal = if (isSmallScreen) 12.dp else 14.dp,
                                    vertical = if (isSmallScreen) 8.dp else 12.dp
                                )
                        ) {
                            Column(modifier = Modifier.fillMaxWidth()) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { isVoiceCallOptEnabled = !isVoiceCallOptEnabled },
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Switch(
                                        checked = isVoiceCallOptEnabled,
                                        onCheckedChange = { isVoiceCallOptEnabled = it },
                                        colors = SwitchDefaults.colors(
                                            checkedThumbColor = Color.White,
                                            checkedTrackColor = Color(0xFF059669),
                                            uncheckedThumbColor = colors.textSecondary,
                                            uncheckedTrackColor = if (colors.isDark) Color(0xFF1E293B) else Color(0xFFCBD5E1)
                                        )
                                    )

                                    Column(
                                        modifier = Modifier
                                            .weight(1f)
                                            .padding(end = 10.dp),
                                        horizontalAlignment = Alignment.End
                                    ) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            Text(
                                                text = "حالت تماس صوتی و کلاب‌هاوس (Voice Call)",
                                                fontSize = if (isSmallScreen) 12.5.sp else 13.5.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = colors.textPrimary,
                                                textAlign = TextAlign.Right
                                            )
                                            Icon(
                                                imageVector = Icons.Default.PhoneInTalk,
                                                contentDescription = null,
                                                tint = Color(0xFF10B981),
                                                modifier = Modifier.size(15.dp)
                                            )
                                        }
                                        Text(
                                            text = if (isVoiceCallOptEnabled)
                                                "فعال: اتصال انحصاری به سرورهای دارای پروتکل UDP کامل (رفع قطعی صدا در کلاب‌هاوس، دیسکورد، تلگرام و واتساپ)"
                                            else
                                                "غیرفعال: اتصال بر اساس پینگ به تمامی سرورها بدون فیلتر UDP",
                                            fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                            color = if (isVoiceCallOptEnabled) Color(0xFF10B981) else colors.textSecondary,
                                            textAlign = TextAlign.Right
                                        )
                                    }
                                }

                                // Live UDP Connectivity Test Button
                                if (isVpnConnected) {
                                    Spacer(modifier = Modifier.height(8.dp))
                                    HorizontalDivider(
                                        color = colors.textSecondary.copy(alpha = 0.2f),
                                        thickness = 0.5.dp
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))

                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Button(
                                            onClick = {
                                                if (!isUdpTesting) {
                                                    isUdpTesting = true
                                                    udpTestStatus = "در حال تست ارسال بسته‌های صوتی UDP..."
                                                    coroutineScope.launch {
                                                        val res = PingTester.testLiveUdpConnectivity()
                                                        isUdpTesting = false
                                                        if (res.isSuccess) {
                                                            udpTestStatus = "✅ ${res.message}"
                                                            try {
                                                                val prefs = PreferencesManager(context)
                                                                val activeRemark = prefs.selectedServerRemark
                                                                val activeNode = VpnRepository(context).getCachedNodes().firstOrNull { it.remark == activeRemark }
                                                                if (activeNode != null) {
                                                                    com.asanvpn.app.data.NodeMetricsCache.saveVoiceCallCompatibility(activeNode, true)
                                                                }
                                                            } catch (_: Exception) {}
                                                        } else {
                                                            udpTestStatus = "❌ ${res.message}"
                                                        }
                                                    }
                                                }
                                            },
                                            enabled = !isUdpTesting,
                                            colors = ButtonDefaults.buttonColors(
                                                containerColor = Color(0xFF10B981).copy(alpha = 0.15f),
                                                contentColor = Color(0xFF10B981)
                                            ),
                                            shape = RoundedCornerShape(10.dp),
                                            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp)
                                        ) {
                                            if (isUdpTesting) {
                                                CircularProgressIndicator(
                                                    modifier = Modifier.size(12.dp),
                                                    color = Color(0xFF10B981),
                                                    strokeWidth = 2.dp
                                                )
                                                Spacer(modifier = Modifier.width(4.dp))
                                            }
                                            Text(
                                                text = if (isUdpTesting) "در حال تست..." else "تست ارسال UDP و صدا",
                                                fontSize = 10.5.sp,
                                                fontWeight = FontWeight.Bold
                                            )
                                        }

                                        if (udpTestStatus != null) {
                                            Text(
                                                text = udpTestStatus ?: "",
                                                fontSize = 10.sp,
                                                color = if (udpTestStatus?.startsWith("✅") == true) colors.jadeGreen else Color(0xFFEF4444),
                                                textAlign = TextAlign.Right,
                                                modifier = Modifier.weight(1f).padding(start = 6.dp),
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // IF WHITELIST IS DISABLED:
                    if (!isEnabled) {
                        item(key = "whitelist_disabled_info") {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .luxuryWell(shape = RoundedCornerShape(16.dp))
                                    .padding(12.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "💡 در این حالت تمام ترافیک و نرم‌افزارهای دستگاه از فیلترشکن عبور می‌کنند. برای تفکیک و انتخاب برنامه‌های خاص، کلید «حالت لیست سفید» بالا را روشن کنید.",
                                    fontSize = if (isSmallScreen) 10.sp else 11.sp,
                                    color = colors.textSecondary,
                                    textAlign = TextAlign.Center,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    } else {
                        // IF WHITELIST IS ENABLED:
                        // Search bar
                        item(key = "app_search_bar") {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .luxuryWell(shape = RoundedCornerShape(14.dp))
                                    .padding(horizontal = 10.dp, vertical = 2.dp)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Search,
                                        contentDescription = "جستجو",
                                        tint = colors.textSecondary,
                                        modifier = Modifier.size(16.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    TextField(
                                        value = searchQuery,
                                        onValueChange = { searchQuery = it },
                                        placeholder = {
                                            Text(
                                                text = "جستجوی نام یا شناسه برنامه...",
                                                fontSize = 11.5.sp,
                                                color = colors.textSecondary.copy(alpha = 0.7f)
                                            )
                                        },
                                        modifier = Modifier.weight(1f),
                                        singleLine = true,
                                        colors = TextFieldDefaults.colors(
                                            focusedContainerColor = Color.Transparent,
                                            unfocusedContainerColor = Color.Transparent,
                                            focusedIndicatorColor = Color.Transparent,
                                            unfocusedIndicatorColor = Color.Transparent,
                                            cursorColor = colors.jadeGreen,
                                            focusedTextColor = colors.textPrimary,
                                            unfocusedTextColor = colors.textPrimary
                                        )
                                    )
                                    if (searchQuery.isNotEmpty()) {
                                        IconButton(
                                            onClick = { searchQuery = "" },
                                            modifier = Modifier.size(22.dp)
                                        ) {
                                            Icon(
                                                imageVector = Icons.Default.Clear,
                                                contentDescription = "پاک کردن",
                                                tint = colors.textSecondary,
                                                modifier = Modifier.size(14.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // Quick Action Buttons
                        item(key = "app_quick_actions") {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(colors.jadeGreen.copy(alpha = 0.15f))
                                        .padding(horizontal = 8.dp, vertical = 3.dp)
                                ) {
                                    Text(
                                        text = "${selectedPackages.size} برنامه انتخاب شده",
                                        fontSize = 10.5.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = colors.jadeGreen
                                    )
                                }

                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text(
                                        text = "انتخاب همه",
                                        fontSize = 10.5.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = colors.skyBlue,
                                        modifier = Modifier
                                            .clickable {
                                                for (app in filteredApps) {
                                                    if (!selectedPackages.contains(app.packageName)) {
                                                        selectedPackages.add(app.packageName)
                                                    }
                                                }
                                            }
                                            .padding(2.dp)
                                    )
                                    Text(
                                        text = "|",
                                        fontSize = 10.5.sp,
                                        color = colors.textSecondary.copy(alpha = 0.4f)
                                    )
                                    Text(
                                        text = "لغو همه",
                                        fontSize = 10.5.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = colors.coralRed,
                                        modifier = Modifier
                                            .clickable {
                                                selectedPackages.clear()
                                            }
                                            .padding(2.dp)
                                    )
                                }
                            }
                        }

                        // App items
                        if (isLoading) {
                            item(key = "loading_apps") {
                                Column(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(120.dp),
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.Center
                                ) {
                                    CircularProgressIndicator(
                                        color = colors.jadeGreen,
                                        modifier = Modifier.size(28.dp),
                                        strokeWidth = 2.5.dp
                                    )
                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = "درحال بارگذاری لیست برنامه‌ها...",
                                        fontSize = 11.sp,
                                        color = colors.textSecondary
                                    )
                                }
                            }
                        } else if (filteredApps.isEmpty()) {
                            item(key = "no_apps_found") {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(80.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(
                                        text = if (searchQuery.isNotEmpty()) "برنامه‌ای با این مشخصات یافت نشد" else "هیچ برنامه‌ای یافت نشد",
                                        fontSize = 11.5.sp,
                                        color = colors.textSecondary
                                    )
                                }
                            }
                        } else {
                            items(filteredApps, key = { it.packageName }) { app ->
                                val isSelected = selectedPackages.contains(app.packageName)
                                val isPopular = app.packageName in AppFilterHelper.POPULAR_PACKAGES

                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(12.dp))
                                        .background(
                                            if (isSelected) colors.jadeGreen.copy(alpha = 0.08f) else Color.Transparent
                                        )
                                        .clickable(enabled = isEnabled) {
                                            if (isSelected) {
                                                selectedPackages.remove(app.packageName)
                                            } else {
                                                selectedPackages.add(app.packageName)
                                            }
                                        }
                                        .padding(horizontal = 8.dp, vertical = 4.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Checkbox(
                                        checked = isSelected,
                                        onCheckedChange = { checked ->
                                            if (checked) {
                                                if (!selectedPackages.contains(app.packageName)) {
                                                    selectedPackages.add(app.packageName)
                                                }
                                            } else {
                                                selectedPackages.remove(app.packageName)
                                            }
                                        },
                                        enabled = isEnabled,
                                        colors = CheckboxDefaults.colors(
                                            checkedColor = colors.jadeGreen,
                                            uncheckedColor = colors.textSecondary.copy(alpha = 0.5f),
                                            checkmarkColor = Color.White
                                        )
                                    )

                                    Column(
                                        modifier = Modifier
                                            .weight(1f)
                                            .padding(horizontal = 6.dp),
                                        horizontalAlignment = Alignment.End
                                    ) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            if (isPopular) {
                                                Box(
                                                    modifier = Modifier
                                                        .clip(RoundedCornerShape(4.dp))
                                                        .background(Color(0xFFF59E0B).copy(alpha = 0.15f))
                                                        .padding(horizontal = 4.dp, vertical = 1.dp)
                                                ) {
                                                    Text(
                                                        text = "محبوب",
                                                        fontSize = 8.5.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color(0xFFF59E0B)
                                                    )
                                                }
                                            }
                                            Text(
                                                text = app.name,
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = if (isEnabled) colors.textPrimary else colors.textSecondary,
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis,
                                                textAlign = TextAlign.Right
                                            )
                                        }
                                        Text(
                                            text = app.packageName,
                                            fontSize = 9.5.sp,
                                            color = colors.textSecondary.copy(alpha = 0.7f),
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                            textAlign = TextAlign.Right
                                        )
                                    }

                                    if (app.iconBitmap != null) {
                                        Image(
                                            bitmap = app.iconBitmap.asImageBitmap(),
                                            contentDescription = app.name,
                                            modifier = Modifier
                                                .size(30.dp)
                                                .clip(RoundedCornerShape(8.dp))
                                        )
                                    } else {
                                        Box(
                                            modifier = Modifier
                                                .size(30.dp)
                                                .clip(RoundedCornerShape(8.dp))
                                                .background(if (colors.isDark) Color(0xFF1E293B) else Color(0xFFE2E8F0)),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            Icon(
                                                imageVector = Icons.Default.Android,
                                                contentDescription = null,
                                                tint = colors.textSecondary,
                                                modifier = Modifier.size(16.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ==================== 3. FIXED FOOTER (ALWAYS VISIBLE & PINNED AT BOTTOM) ====================
                Spacer(modifier = Modifier.height(if (isSmallScreen) 6.dp else 10.dp))

                if (isVpnConnected) {
                    Text(
                        text = "⚡ جهت اعمال قوانین جدید، پس از ذخیره ارتباط یک‌بار بازنشانی می‌شود.",
                        fontSize = if (isSmallScreen) 9.5.sp else 10.5.sp,
                        color = colors.amberWarning,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(bottom = if (isSmallScreen) 2.dp else 4.dp)
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier
                            .weight(1f)
                            .height(if (isSmallScreen) 40.dp else 46.dp),
                        shape = RoundedCornerShape(if (isSmallScreen) 12.dp else 16.dp),
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            colors.textSecondary.copy(alpha = 0.3f)
                        )
                    ) {
                        Text(
                            text = "انصراف",
                            fontSize = if (isSmallScreen) 12.sp else 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = colors.textSecondary
                        )
                    }

                    Button(
                        onClick = {
                            if (isEnabled && selectedPackages.isEmpty()) {
                                Toast.makeText(
                                    context,
                                    "لطفاً حداقل یک برنامه را انتخاب کنید یا فیلتر را خاموش نمایید",
                                    Toast.LENGTH_SHORT
                                ).show()
                                return@Button
                            }
                            onSave(isEnabled, selectedPackages.toSet(), isSpeedOptEnabled, isGeminiOptEnabled, isVoiceCallOptEnabled)
                            onDismiss()
                        },
                        modifier = Modifier
                            .weight(1.5f)
                            .height(if (isSmallScreen) 40.dp else 46.dp),
                        shape = RoundedCornerShape(if (isSmallScreen) 12.dp else 16.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color.Transparent
                        ),
                        contentPadding = PaddingValues()
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(
                                    Brush.horizontalGradient(
                                        listOf(Color(0xFF059669), Color(0xFF10B981), Color(0xFF34D399))
                                    ),
                                    shape = RoundedCornerShape(if (isSmallScreen) 12.dp else 16.dp)
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Check,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(if (isSmallScreen) 16.dp else 18.dp)
                                )
                                Text(
                                    text = "ذخیره و اعمال تنظیمات",
                                    color = Color.White,
                                    fontSize = if (isSmallScreen) 12.sp else 13.5.sp,
                                    fontWeight = FontWeight.ExtraBold
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
