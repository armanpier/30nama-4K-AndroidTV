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
import com.asanvpn.app.util.AppFilterHelper
import com.asanvpn.app.util.AppFilterItem
import kotlinx.coroutines.launch

@Composable
fun AppFilterDialog(
    initialEnabled: Boolean,
    initialWhitelist: Set<String>,
    initialSpeedOptEnabled: Boolean = false,
    isVpnConnected: Boolean,
    onDismiss: () -> Unit,
    onSave: (enabled: Boolean, whitelist: Set<String>, speedOptEnabled: Boolean) -> Unit
) {
    val context = LocalContext.current
    val colors = LuxuryTheme.colors
    val coroutineScope = rememberCoroutineScope()

    var isEnabled by remember { mutableStateOf(initialEnabled) }
    var isSpeedOptEnabled by remember { mutableStateOf(initialSpeedOptEnabled) }
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
                .fillMaxWidth(0.94f)
                .fillMaxHeight(0.88f)
                .luxuryCushion(shape = RoundedCornerShape(28.dp), elevation = 12.dp)
                .padding(20.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // ==================== HEADER ====================
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
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Tune,
                                contentDescription = null,
                                tint = colors.jadeGreen,
                                modifier = Modifier.size(20.dp)
                            )
                            Text(
                                text = "فیلتر برنامه‌ها (App Filter)",
                                fontSize = 17.sp,
                                fontWeight = FontWeight.Black,
                                color = colors.textPrimary,
                                textAlign = TextAlign.Center
                            )
                        }
                        Text(
                            text = "انتخاب برنامه‌های مجاز جهت عبور از فیلترشکن",
                            fontSize = 11.5.sp,
                            color = colors.textSecondary,
                            textAlign = TextAlign.Center
                        )
                    }

                    Box(
                        modifier = Modifier
                            .size(36.dp)
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
                            modifier = Modifier.size(18.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // ==================== MASTER SWITCH CARD ====================
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(shape = RoundedCornerShape(20.dp), elevation = 4.dp)
                        .border(
                            1.dp,
                            if (isEnabled) colors.jadeGreen.copy(alpha = 0.4f) else Color.Transparent,
                            RoundedCornerShape(20.dp)
                        )
                        .clickable { isEnabled = !isEnabled }
                        .padding(horizontal = 14.dp, vertical = 12.dp)
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
                                fontSize = 13.5.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.textPrimary,
                                textAlign = TextAlign.Right
                            )
                            Text(
                                text = if (isEnabled)
                                    "فقط برنامه‌های تیک‌خورده (${selectedPackages.size} برنامه) از فیلترشکن رد می‌شوند"
                                else
                                    "غیرفعال: تمام ترافیک دستگاه از فیلترشکن عبور می‌کند",
                                fontSize = 11.sp,
                                color = if (isEnabled) colors.jadeGreen else colors.textSecondary,
                                textAlign = TextAlign.Right
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // ==================== SPEED OPTIMIZATION CARD ====================
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(shape = RoundedCornerShape(20.dp), elevation = 4.dp)
                        .border(
                            1.dp,
                            if (isSpeedOptEnabled) Color(0xFF38BDF8).copy(alpha = 0.4f) else Color.Transparent,
                            RoundedCornerShape(20.dp)
                        )
                        .clickable { isSpeedOptEnabled = !isSpeedOptEnabled }
                        .padding(horizontal = 14.dp, vertical = 12.dp)
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
                                    fontSize = 13.5.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.textPrimary,
                                    textAlign = TextAlign.Right
                                )
                                Icon(
                                    imageVector = Icons.Default.Speed,
                                    contentDescription = null,
                                    tint = Color(0xFF38BDF8),
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                            Text(
                                text = if (isSpeedOptEnabled)
                                    "فعال: تست ۵ سرور برتر با دانلود بسته ۱۰ مگابایت در پس‌زمینه و سوییچ به پرسرعت‌ترین سرور"
                                else
                                    "غیرفعال: اتصال طبق کمترین پینگ (پیش‌فرض، جهت صرفه‌جویی باتری و اینترنت)",
                                fontSize = 11.sp,
                                color = if (isSpeedOptEnabled) Color(0xFF38BDF8) else colors.textSecondary,
                                textAlign = TextAlign.Right
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // ==================== SEARCH BAR & CONTROLS ====================
                if (isEnabled) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .luxuryWell(shape = RoundedCornerShape(16.dp))
                            .padding(horizontal = 12.dp, vertical = 2.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Search,
                                contentDescription = "جستجو",
                                tint = colors.textSecondary,
                                modifier = Modifier.size(18.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            TextField(
                                value = searchQuery,
                                onValueChange = { searchQuery = it },
                                placeholder = {
                                    Text(
                                        text = "جستجوی نام یا شناسه برنامه...",
                                        fontSize = 12.sp,
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
                                    modifier = Modifier.size(24.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Clear,
                                        contentDescription = "پاک کردن",
                                        tint = colors.textSecondary,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Quick Action Buttons Row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Badge count
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(10.dp))
                                .background(colors.jadeGreen.copy(alpha = 0.15f))
                                .padding(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = "${selectedPackages.size} برنامه انتخاب شده",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = colors.jadeGreen
                            )
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(
                                text = "انتخاب همه",
                                fontSize = 11.sp,
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
                                    .padding(4.dp)
                            )
                            Text(
                                text = "|",
                                fontSize = 11.sp,
                                color = colors.textSecondary.copy(alpha = 0.4f)
                            )
                            Text(
                                text = "لغو همه",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = colors.coralRed,
                                modifier = Modifier
                                    .clickable {
                                        selectedPackages.clear()
                                    }
                                    .padding(4.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                }

                // ==================== APP LIST (LAZY COLUMN) ====================
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .luxuryWell(shape = RoundedCornerShape(18.dp))
                        .padding(horizontal = 4.dp, vertical = 6.dp)
                ) {
                    when {
                        isLoading -> {
                            Column(
                                modifier = Modifier.fillMaxSize(),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                CircularProgressIndicator(
                                    color = colors.jadeGreen,
                                    modifier = Modifier.size(36.dp),
                                    strokeWidth = 3.dp
                                )
                                Spacer(modifier = Modifier.height(12.dp))
                                Text(
                                    text = "درحال بارگذاری لیست برنامه‌ها...",
                                    fontSize = 12.sp,
                                    color = colors.textSecondary
                                )
                            }
                        }
                        filteredApps.isEmpty() -> {
                            Box(
                                modifier = Modifier.fillMaxSize(),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = if (searchQuery.isNotEmpty()) "برنامه‌ای با این نام یافت نشد" else "هیچ برنامه‌ای یافت نشد",
                                    fontSize = 12.sp,
                                    color = colors.textSecondary
                                )
                            }
                        }
                        else -> {
                            LazyColumn(
                                modifier = Modifier.fillMaxSize(),
                                verticalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                items(filteredApps, key = { it.packageName }) { app ->
                                    val isSelected = selectedPackages.contains(app.packageName)
                                    val isPopular = app.packageName in AppFilterHelper.POPULAR_PACKAGES

                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clip(RoundedCornerShape(14.dp))
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
                                            .padding(horizontal = 10.dp, vertical = 6.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        // Left: Checkbox (or visual state)
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

                                        // Center: App Name & Package
                                        Column(
                                            modifier = Modifier
                                                .weight(1f)
                                                .padding(horizontal = 8.dp),
                                            horizontalAlignment = Alignment.End
                                        ) {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                                            ) {
                                                if (isPopular) {
                                                    Box(
                                                        modifier = Modifier
                                                            .clip(RoundedCornerShape(6.dp))
                                                            .background(Color(0xFFF59E0B).copy(alpha = 0.15f))
                                                            .padding(horizontal = 5.dp, vertical = 1.dp)
                                                    ) {
                                                        Text(
                                                            text = "محبوب",
                                                            fontSize = 9.sp,
                                                            fontWeight = FontWeight.Bold,
                                                            color = Color(0xFFF59E0B)
                                                        )
                                                    }
                                                }
                                                Text(
                                                    text = app.name,
                                                    fontSize = 13.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = if (isEnabled) colors.textPrimary else colors.textSecondary,
                                                    maxLines = 1,
                                                    overflow = TextOverflow.Ellipsis,
                                                    textAlign = TextAlign.Right
                                                )
                                            }
                                            Text(
                                                text = app.packageName,
                                                fontSize = 10.sp,
                                                color = colors.textSecondary.copy(alpha = 0.7f),
                                                maxLines = 1,
                                                overflow = TextOverflow.Ellipsis,
                                                textAlign = TextAlign.Right
                                            )
                                        }

                                        // Right: App Icon
                                        if (app.iconBitmap != null) {
                                            Image(
                                                bitmap = app.iconBitmap.asImageBitmap(),
                                                contentDescription = app.name,
                                                modifier = Modifier
                                                    .size(36.dp)
                                                    .clip(RoundedCornerShape(10.dp))
                                            )
                                        } else {
                                            Box(
                                                modifier = Modifier
                                                    .size(36.dp)
                                                    .clip(RoundedCornerShape(10.dp))
                                                    .background(if (colors.isDark) Color(0xFF1E293B) else Color(0xFFE2E8F0)),
                                                contentAlignment = Alignment.Center
                                            ) {
                                                Icon(
                                                    imageVector = Icons.Default.Android,
                                                    contentDescription = null,
                                                    tint = colors.textSecondary,
                                                    modifier = Modifier.size(20.dp)
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // ==================== NOTICE & FOOTER BUTTONS ====================
                if (isVpnConnected) {
                    Text(
                        text = "⚡ جهت اعمال قوانین جدید فیلتر، پس از ذخیره ارتباط یک‌بار بازنشانی می‌شود.",
                        fontSize = 10.5.sp,
                        color = colors.amberWarning,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier
                            .weight(1f)
                            .height(46.dp),
                        shape = RoundedCornerShape(16.dp),
                        border = androidx.compose.foundation.BorderStroke(
                            1.dp,
                            colors.textSecondary.copy(alpha = 0.3f)
                        )
                    ) {
                        Text(
                            text = "انصراف",
                            fontSize = 13.sp,
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
                            onSave(isEnabled, selectedPackages.toSet(), isSpeedOptEnabled)
                            onDismiss()
                        },
                        modifier = Modifier
                            .weight(1.5f)
                            .height(46.dp),
                        shape = RoundedCornerShape(16.dp),
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
                                    shape = RoundedCornerShape(16.dp)
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
                                    modifier = Modifier.size(18.dp)
                                )
                                Text(
                                    text = "ذخیره و اعمال فیلتر",
                                    color = Color.White,
                                    fontSize = 13.5.sp,
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
