package com.asanvpn.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.asanvpn.app.data.models.VpnNode
import com.asanvpn.app.ui.theme.LuxuryTheme
import com.asanvpn.app.ui.theme.luxuryCushion
import com.asanvpn.app.ui.theme.luxuryWell
import kotlinx.coroutines.launch

@Composable
fun ServerSelectionDialog(
    availableNodes: List<VpnNode>,
    currentSelectedRemark: String?,
    currentServerPing: Long = 0L,
    isAutoServerMode: Boolean,
    onDismiss: () -> Unit,
    onSelectAuto: () -> Unit,
    onSelectNode: (VpnNode) -> Unit,
    isPinging: Boolean = false,
    onRefreshPing: (() -> Unit)? = null
) {
    val colors = LuxuryTheme.colors
    val configuration = LocalConfiguration.current
    val screenHeight = configuration.screenHeightDp.dp
    val screenWidth = configuration.screenWidthDp.dp
    val isSmallScreen = screenHeight < 680.dp || screenWidth <= 365.dp

    var searchQuery by remember { mutableStateOf("") }
    var showSpeedTestDialog by remember { mutableStateOf(false) }

    // Identify highest priority panel (lowest integer priority value)
    val topPriority = remember(availableNodes) {
        availableNodes.mapNotNull { it.panelPriority }.minOrNull() ?: 1
    }

    // In manual mode: strictly filter to only nodes belonging to the top priority panel!
    val candidateNodes = remember(availableNodes, topPriority) {
        val top = availableNodes.filter { (it.panelPriority ?: 1) == topPriority }
        if (top.isNotEmpty()) top else availableNodes
    }

    // Automatically trigger fresh ping & throughput if any candidate node has not been pinged or speed tested yet
    LaunchedEffect(candidateNodes) {
        val hasUntestedLatency = candidateNodes.any {
            it.latencyMs == 0L && com.asanvpn.app.data.NodeMetricsCache.getLatency(it) == null
        }
        val hasUntestedSpeed = candidateNodes.any {
            (it.downloadSpeedMBs == null || it.downloadSpeedMBs!! <= 0.0) &&
            com.asanvpn.app.data.NodeMetricsCache.getSpeed(it) == null
        }
        if ((hasUntestedLatency || hasUntestedSpeed) && onRefreshPing != null && !isPinging) {
            onRefreshPing()
        }
    }

    val distinctPanelNames = remember(candidateNodes) {
        candidateNodes.mapNotNull { it.panelName?.trim() }.filter { it.isNotBlank() }.distinct()
    }

    val topPanelName = remember(distinctPanelNames) {
        when {
            distinctPanelNames.isEmpty() -> "پنل اولویت ۱"
            distinctPanelNames.size == 1 -> distinctPanelNames.first()
            distinctPanelNames.size == 2 -> "${distinctPanelNames[0]} و ${distinctPanelNames[1]}"
            else -> "همه پنل‌های اولویت ۱"
        }
    }

    var selectedPanelFilter by remember { mutableStateOf<String?>(null) }

    val filteredNodes = remember(candidateNodes, searchQuery, selectedPanelFilter) {
        var list = candidateNodes
        if (!selectedPanelFilter.isNullOrBlank()) {
            list = list.filter { it.panelName == selectedPanelFilter }
        }
        if (searchQuery.isNotBlank()) {
            val q = searchQuery.trim().lowercase()
            list = list.filter { node ->
                node.remark.lowercase().contains(q) ||
                (node.panelName?.lowercase()?.contains(q) == true) ||
                node.server.lowercase().contains(q)
            }
        }
        list
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
                // ==================== HEADER ====================
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

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "انتخاب سرور",
                            fontSize = if (isSmallScreen) 15.sp else 17.sp,
                            fontWeight = FontWeight.Black,
                            color = colors.textPrimary
                        )
                        Text(
                            text = "سرورهای منتخب • ${filteredNodes.size} سرور در دسترس",
                            fontSize = if (isSmallScreen) 10.sp else 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = colors.jadeGreen
                        )
                    }

                    Box(
                        modifier = Modifier
                            .size(if (isSmallScreen) 32.dp else 36.dp)
                            .luxuryWell(shape = CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Dns,
                            contentDescription = null,
                            tint = colors.skyBlue,
                            modifier = Modifier.size(if (isSmallScreen) 16.dp else 18.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(if (isSmallScreen) 8.dp else 14.dp))

                // ==================== SEARCH BAR ====================
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryWell(shape = RoundedCornerShape(if (isSmallScreen) 14.dp else 16.dp))
                        .padding(horizontal = 10.dp, vertical = if (isSmallScreen) 2.dp else 4.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Search,
                            contentDescription = null,
                            tint = colors.textSecondary,
                            modifier = Modifier.size(if (isSmallScreen) 16.dp else 18.dp)
                        )

                        OutlinedTextField(
                            value = searchQuery,
                            onValueChange = { searchQuery = it },
                            placeholder = {
                                Text(
                                    text = "جستجوی سرور (نام، کشور، پنل)...",
                                    fontSize = if (isSmallScreen) 11.5.sp else 12.sp,
                                    color = colors.textMuted
                                )
                            },
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = Color.Transparent,
                                unfocusedBorderColor = Color.Transparent,
                                focusedTextColor = colors.textPrimary,
                                unfocusedTextColor = colors.textPrimary
                            ),
                            modifier = Modifier.weight(1f)
                        )

                        if (searchQuery.isNotBlank()) {
                            IconButton(
                                onClick = { searchQuery = "" },
                                modifier = Modifier.size(if (isSmallScreen) 22.dp else 24.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Clear,
                                    contentDescription = "پاک کردن",
                                    tint = colors.textSecondary,
                                    modifier = Modifier.size(if (isSmallScreen) 14.dp else 16.dp)
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(if (isSmallScreen) 8.dp else 12.dp))

                // ==================== AUTO MODE CARD ====================
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .luxuryCushion(
                            shape = RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp),
                            elevation = 4.dp
                        )
                        .border(
                            width = if (isAutoServerMode) 1.5.dp else 0.dp,
                            color = if (isAutoServerMode) colors.jadeGreen else Color.Transparent,
                            shape = RoundedCornerShape(if (isSmallScreen) 16.dp else 20.dp)
                        )
                        .clickable { onSelectAuto() }
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
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            RadioButton(
                                selected = isAutoServerMode,
                                onClick = { onSelectAuto() },
                                colors = RadioButtonDefaults.colors(selectedColor = colors.jadeGreen)
                            )
                        }

                        Column(
                            horizontalAlignment = Alignment.End,
                            modifier = Modifier.weight(1f).padding(horizontal = 8.dp)
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Text(
                                    text = "انتخاب هوشمند خودکار (پیشنهادی)",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.ExtraBold,
                                    color = if (isAutoServerMode) colors.jadeGreen else colors.textPrimary,
                                    textAlign = TextAlign.Right
                                )
                                Box(
                                    modifier = Modifier
                                        .size(24.dp)
                                        .clip(CircleShape)
                                        .background(colors.jadeGreen.copy(alpha = 0.15f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Bolt,
                                        contentDescription = null,
                                        tint = colors.jadeGreen,
                                        modifier = Modifier.size(15.dp)
                                    )
                                }
                            }
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = "اتصال خودکار به کم‌تاخیرترین و پایدارترین سرور",
                                fontSize = 10.5.sp,
                                color = colors.textSecondary,
                                textAlign = TextAlign.Right
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        if (onRefreshPing != null) {
                            Box(
                                modifier = Modifier
                                    .size(28.dp)
                                    .luxuryCushion(shape = CircleShape, elevation = 2.dp)
                                    .clip(CircleShape)
                                    .clickable(enabled = !isPinging) { onRefreshPing() },
                                contentAlignment = Alignment.Center
                            ) {
                                if (isPinging) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(13.dp),
                                        strokeWidth = 2.dp,
                                        color = colors.skyBlue
                                    )
                                } else {
                                    Icon(
                                        imageVector = Icons.Default.Refresh,
                                        contentDescription = "بروزرسانی پینگ",
                                        tint = colors.skyBlue,
                                        modifier = Modifier.size(15.dp)
                                    )
                                }
                            }
                        }
                        Text(
                            text = "تعداد: ${filteredNodes.size}",
                            fontSize = 10.5.sp,
                            color = colors.textMuted
                        )
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(colors.skyBlue.copy(alpha = 0.14f))
                                .clickable { showSpeedTestDialog = true }
                                .padding(horizontal = 7.dp, vertical = 3.dp)
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(3.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Speed,
                                    contentDescription = "سنجش سرعت دستی",
                                    tint = colors.skyBlue,
                                    modifier = Modifier.size(12.dp)
                                )
                                Text(
                                    text = "سنجش سرعت",
                                    fontSize = if (isSmallScreen) 9.sp else 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = colors.skyBlue
                                )
                            }
                        }
                    }
                    Text(
                        text = "سرورهای منتخب (اولویت ۱)",
                        fontSize = 11.5.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textSecondary
                    )
                }

                if (distinctPanelNames.size > 1) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        val isAllSelected = selectedPanelFilter == null
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(10.dp))
                                .background(if (isAllSelected) colors.skyBlue.copy(alpha = 0.18f) else colors.textMuted.copy(alpha = 0.08f))
                                .border(
                                    width = if (isAllSelected) 1.dp else 0.dp,
                                    color = if (isAllSelected) colors.skyBlue else Color.Transparent,
                                    shape = RoundedCornerShape(10.dp)
                                )
                                .clickable { selectedPanelFilter = null }
                                .padding(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Text(
                                text = "همه (${candidateNodes.size})",
                                fontSize = 11.sp,
                                fontWeight = if (isAllSelected) FontWeight.Bold else FontWeight.Medium,
                                color = if (isAllSelected) colors.skyBlue else colors.textSecondary
                            )
                        }

                        for (pName in distinctPanelNames) {
                            val count = candidateNodes.count { it.panelName == pName }
                            val isSelected = selectedPanelFilter == pName
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(if (isSelected) colors.skyBlue.copy(alpha = 0.18f) else colors.textMuted.copy(alpha = 0.08f))
                                    .border(
                                        width = if (isSelected) 1.dp else 0.dp,
                                        color = if (isSelected) colors.skyBlue else Color.Transparent,
                                        shape = RoundedCornerShape(10.dp)
                                    )
                                    .clickable { selectedPanelFilter = pName }
                                    .padding(horizontal = 10.dp, vertical = 4.dp)
                            ) {
                                Text(
                                    text = "$pName ($count)",
                                    fontSize = 11.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                    color = if (isSelected) colors.skyBlue else colors.textSecondary
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                // ==================== SCROLLABLE SERVER LIST ====================
                if (filteredNodes.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "سروری با این مشخصات یافت نشد",
                            fontSize = 13.sp,
                            color = colors.textSecondary
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        itemsIndexed(
                            items = filteredNodes,
                            key = { index, node -> "${index}_${node.server}_${node.port}_${node.remark}_${node.latencyMs}_${node.downloadSpeedMBs ?: 0.0}" }
                        ) { index, node ->
                            val rawRemark = node.remark ?: ""
                            val remarkSafe = if (rawRemark.isNotBlank()) rawRemark else "سرور ${index + 1}"
                            val isSelected = !isAutoServerMode && (
                                remarkSafe.trim().equals(currentSelectedRemark?.trim(), ignoreCase = true) ||
                                rawRemark.trim().equals(currentSelectedRemark?.trim(), ignoreCase = true)
                            )

                            val isCurrentlyConnected = currentSelectedRemark != null && (
                                remarkSafe.trim().equals(currentSelectedRemark.trim(), ignoreCase = true) ||
                                rawRemark.trim().equals(currentSelectedRemark.trim(), ignoreCase = true) ||
                                (currentSelectedRemark.isNotBlank() && (remarkSafe.contains(currentSelectedRemark, ignoreCase = true) || currentSelectedRemark.contains(remarkSafe, ignoreCase = true)))
                            )

                            val measuredLatency = if (isCurrentlyConnected && currentServerPing > 0) {
                                currentServerPing
                            } else if (node.latencyMs != 0L) {
                                node.latencyMs
                            } else {
                                com.asanvpn.app.data.NodeMetricsCache.getLatency(node) ?: 0L
                            }

                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .defaultMinSize(minHeight = if (isSmallScreen) 54.dp else 58.dp)
                                    .luxuryCushion(shape = RoundedCornerShape(16.dp), elevation = 3.dp)
                                    .border(
                                        width = if (isSelected) 1.5.dp else 0.dp,
                                        color = if (isSelected) colors.skyBlue else Color.Transparent,
                                        shape = RoundedCornerShape(16.dp)
                                    )
                                    .clickable { onSelectNode(node) }
                                    .padding(
                                        horizontal = if (isSmallScreen) 10.dp else 12.dp,
                                        vertical = if (isSmallScreen) 7.dp else 9.dp
                                    )
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    // Left: Custom Radio indicator + Metrics Column (Latency on top, Speed below if tested)
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(if (isSmallScreen) 6.dp else 8.dp)
                                    ) {
                                        // Custom Radio Button (no 48dp touch target padding bloat)
                                        Box(
                                            modifier = Modifier
                                                .size(18.dp)
                                                .clip(CircleShape)
                                                .border(
                                                    width = if (isSelected) 5.dp else 1.5.dp,
                                                    color = if (isSelected) colors.skyBlue else colors.textMuted.copy(alpha = 0.5f),
                                                    shape = CircleShape
                                                ),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            if (isSelected) {
                                                Box(
                                                    modifier = Modifier
                                                        .size(6.dp)
                                                        .clip(CircleShape)
                                                        .background(Color.White)
                                                )
                                            }
                                        }

                                        val measuredSpeed = node.downloadSpeedMBs ?: com.asanvpn.app.data.NodeMetricsCache.getSpeed(node)
                                        val measuredUpload = node.uploadSpeedMBs ?: com.asanvpn.app.data.NodeMetricsCache.getUploadSpeed(node)

                                        Column(
                                            verticalArrangement = Arrangement.spacedBy(2.5.dp),
                                            horizontalAlignment = Alignment.Start
                                        ) {
                                            // Latency badge
                                            Box(
                                                modifier = Modifier
                                                    .luxuryWell(shape = RoundedCornerShape(8.dp))
                                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                                            ) {
                                                if (measuredLatency > 0) {
                                                    val badgeColor = when {
                                                        measuredLatency < 160 -> colors.jadeGreen
                                                        measuredLatency < 300 -> colors.skyBlue
                                                        else -> Color(0xFFFFA726)
                                                    }
                                                    Text(
                                                        text = "$measuredLatency ms",
                                                        fontSize = if (isSmallScreen) 9.sp else 10.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = badgeColor
                                                    )
                                                } else if (measuredLatency < 0) {
                                                    Text(
                                                        text = "تایم‌اوت",
                                                        fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color(0xFFEF5350)
                                                    )
                                                } else {
                                                    Text(
                                                        text = if (isPinging) "..." else "-- ms",
                                                        fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                                                        fontWeight = FontWeight.Medium,
                                                        color = colors.textMuted
                                                    )
                                                }
                                            }

                                            // Measured download speed badge if tested
                                            if (measuredSpeed != null && measuredSpeed > 0.0) {
                                                val roundedSpeed = (measuredSpeed * 10).toInt() / 10.0
                                                Box(
                                                    modifier = Modifier
                                                        .luxuryWell(shape = RoundedCornerShape(8.dp))
                                                        .padding(horizontal = 5.dp, vertical = 1.5.dp)
                                                ) {
                                                    Row(
                                                        verticalAlignment = Alignment.CenterVertically,
                                                        horizontalArrangement = Arrangement.spacedBy(2.dp)
                                                    ) {
                                                        Icon(
                                                            imageVector = Icons.Default.ArrowDownward,
                                                            contentDescription = null,
                                                            tint = Color(0xFFFFB300),
                                                            modifier = Modifier.size(10.dp)
                                                        )
                                                        Text(
                                                            text = "$roundedSpeed MB/s",
                                                            fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                                                            fontWeight = FontWeight.Bold,
                                                            color = Color(0xFFFFB300)
                                                        )
                                                    }
                                                }
                                            }

                                            // Measured upload speed badge if tested
                                            if (measuredUpload != null && measuredUpload > 0.0) {
                                                val roundedUpload = (measuredUpload * 10).toInt() / 10.0
                                                Box(
                                                    modifier = Modifier
                                                        .luxuryWell(shape = RoundedCornerShape(8.dp))
                                                        .padding(horizontal = 5.dp, vertical = 1.5.dp)
                                                ) {
                                                    Row(
                                                        verticalAlignment = Alignment.CenterVertically,
                                                        horizontalArrangement = Arrangement.spacedBy(2.dp)
                                                    ) {
                                                        Icon(
                                                            imageVector = Icons.Default.ArrowUpward,
                                                            contentDescription = null,
                                                            tint = colors.skyBlue,
                                                            modifier = Modifier.size(10.dp)
                                                        )
                                                        Text(
                                                            text = "$roundedUpload MB/s",
                                                            fontSize = if (isSmallScreen) 8.5.sp else 9.5.sp,
                                                            fontWeight = FontWeight.Bold,
                                                            color = colors.skyBlue
                                                        )
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // Right: Remark Name + Panel Badge + Protocol
                                    Column(
                                        horizontalAlignment = Alignment.End,
                                        modifier = Modifier.weight(1f).padding(start = 10.dp)
                                    ) {
                                        Text(
                                            text = remarkSafe,
                                            fontSize = if (isSmallScreen) 12.sp else 13.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = if (isSelected) colors.skyBlue else colors.textPrimary,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                            textAlign = TextAlign.Right
                                        )

                                        Spacer(modifier = Modifier.height(3.dp))

                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            val proto = (node.protocol ?: "VLESS").uppercase()
                                            val transport = (node.type ?: "TCP").uppercase()
                                            Text(
                                                text = "$proto • $transport",
                                                fontSize = if (isSmallScreen) 8.5.sp else 9.sp,
                                                color = colors.textMuted,
                                                maxLines = 1
                                            )

                                            val panelName = (node.panelName ?: "").ifBlank { "سرور ابری" }
                                            Box(
                                                modifier = Modifier
                                                    .weight(1f, fill = false)
                                                    .clip(RoundedCornerShape(6.dp))
                                                    .background(colors.skyBlue.copy(alpha = 0.12f))
                                                    .padding(horizontal = 5.dp, vertical = 1.5.dp)
                                            ) {
                                                Text(
                                                    text = panelName,
                                                    fontSize = if (isSmallScreen) 8.5.sp else 9.sp,
                                                    fontWeight = FontWeight.SemiBold,
                                                    color = colors.skyBlue,
                                                    maxLines = 1,
                                                    overflow = TextOverflow.Ellipsis
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showSpeedTestDialog) {
        ManualSpeedTestDialog(
            candidateNodes = candidateNodes,
            currentSelectedRemark = currentSelectedRemark,
            onDismiss = { showSpeedTestDialog = false },
            onSelectNode = { selectedNode ->
                showSpeedTestDialog = false
                onSelectNode(selectedNode)
                onDismiss()
            },
            onNodeUpdated = {
                // UI automatically reflects updated metrics from cache and state
            }
        )
    }
}

@Composable
fun ManualSpeedTestDialog(
    candidateNodes: List<VpnNode>,
    currentSelectedRemark: String?,
    onDismiss: () -> Unit,
    onSelectNode: (VpnNode) -> Unit,
    onNodeUpdated: (VpnNode) -> Unit
) {
    val colors = LuxuryTheme.colors
    val configuration = LocalConfiguration.current
    val screenHeight = configuration.screenHeightDp.dp
    val screenWidth = configuration.screenWidthDp.dp
    val isSmallScreen = screenHeight < 680.dp || screenWidth <= 365.dp

    val payloadOptions = listOf(0.5, 1.0, 2.0, 5.0)
    val payloadLabels = listOf("500 KB", "1 MB", "2 MB", "5 MB")
    var selectedPayloadMB by remember { mutableStateOf(5.0) }

    var isTesting by remember { mutableStateOf(false) }
    var activeTestingIndex by remember { mutableStateOf(-1) }
    var testingStage by remember { mutableStateOf("") }
    val coroutineScope = rememberCoroutineScope()

    var testList by remember(candidateNodes) {
        mutableStateOf(candidateNodes.take(5))
    }

    Dialog(
        onDismissRequest = { if (!isTesting) onDismiss() },
        properties = DialogProperties(
            usePlatformDefaultWidth = false,
            dismissOnBackPress = !isTesting,
            dismissOnClickOutside = !isTesting
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(if (isSmallScreen) 0.98f else 0.94f)
                .wrapContentHeight()
                .luxuryCushion(
                    shape = RoundedCornerShape(if (isSmallScreen) 20.dp else 26.dp),
                    elevation = 14.dp
                )
                .padding(if (isSmallScreen) 12.dp else 18.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Header
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(30.dp)
                            .luxuryCushion(shape = CircleShape, elevation = 2.dp)
                            .clickable(enabled = !isTesting) { onDismiss() },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "بستن",
                            tint = if (isTesting) colors.textMuted else colors.textSecondary,
                            modifier = Modifier.size(16.dp)
                        )
                    }

                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(
                            text = "سنجش سرعت دستی لینک‌ها",
                            fontSize = if (isSmallScreen) 14.sp else 16.sp,
                            fontWeight = FontWeight.Black,
                            color = colors.textPrimary
                        )
                        Text(
                            text = "تست نوبتی دانلود و آپلود سرورهای برتر",
                            fontSize = if (isSmallScreen) 9.5.sp else 10.5.sp,
                            color = colors.skyBlue
                        )
                    }

                    Box(
                        modifier = Modifier
                            .size(30.dp)
                            .luxuryWell(shape = CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Speed,
                            contentDescription = null,
                            tint = colors.skyBlue,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Payload Size Selection Chips
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "حجم فایل تست:",
                        fontSize = 11.5.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textSecondary
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        payloadOptions.forEachIndexed { idx, sizeMB ->
                            val isSelected = selectedPayloadMB == sizeMB
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(if (isSelected) colors.skyBlue.copy(alpha = 0.2f) else colors.textMuted.copy(alpha = 0.08f))
                                    .border(
                                        width = if (isSelected) 1.dp else 0.dp,
                                        color = if (isSelected) colors.skyBlue else Color.Transparent,
                                        shape = RoundedCornerShape(8.dp)
                                    )
                                    .clickable(enabled = !isTesting) { selectedPayloadMB = sizeMB }
                                    .padding(horizontal = 7.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    text = payloadLabels[idx],
                                    fontSize = 10.5.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                    color = if (isSelected) colors.skyBlue else colors.textSecondary
                                )
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // Candidate server cards
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    testList.forEachIndexed { index, node ->
                        val isCurrentTesting = isTesting && activeTestingIndex == index
                        val isSelected = node.remark == currentSelectedRemark
                        val measuredDown = node.downloadSpeedMBs ?: com.asanvpn.app.data.NodeMetricsCache.getSpeed(node)
                        val measuredUp = node.uploadSpeedMBs ?: com.asanvpn.app.data.NodeMetricsCache.getUploadSpeed(node)
                        val lat = if (node.latencyMs > 0) node.latencyMs else (com.asanvpn.app.data.NodeMetricsCache.getLatency(node) ?: 0L)

                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .luxuryWell(shape = RoundedCornerShape(12.dp))
                                .border(
                                    width = when {
                                        isCurrentTesting -> 1.5.dp
                                        isSelected -> 1.5.dp
                                        else -> 0.dp
                                    },
                                    color = when {
                                        isCurrentTesting -> colors.amberWarning
                                        isSelected -> colors.skyBlue
                                        else -> Color.Transparent
                                    },
                                    shape = RoundedCornerShape(12.dp)
                                )
                                .clickable {
                                    onSelectNode(node)
                                }
                                .padding(horizontal = 10.dp, vertical = 7.dp)
                        ) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                // Left: Radio/indicator & Metrics badges
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    // Custom Radio selection indicator
                                    Box(
                                        modifier = Modifier
                                            .size(16.dp)
                                            .clip(CircleShape)
                                            .border(
                                                width = if (isSelected) 4.5.dp else 1.5.dp,
                                                color = if (isSelected) colors.skyBlue else colors.textMuted.copy(alpha = 0.5f),
                                                shape = CircleShape
                                            ),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        if (isSelected) {
                                            Box(
                                                modifier = Modifier
                                                    .size(5.dp)
                                                    .clip(CircleShape)
                                                    .background(Color.White)
                                            )
                                        }
                                    }

                                    if (isCurrentTesting) {
                                        CircularProgressIndicator(
                                            modifier = Modifier.size(12.dp),
                                            strokeWidth = 2.dp,
                                            color = colors.amberWarning
                                        )
                                        Text(
                                            text = testingStage,
                                            fontSize = 9.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = colors.amberWarning
                                        )
                                    } else {
                                        // Latency
                                        if (lat > 0) {
                                            Text(
                                                text = "${lat}ms",
                                                fontSize = 9.5.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = colors.jadeGreen
                                            )
                                        }
                                        // Download
                                        if (measuredDown != null && measuredDown > 0.0) {
                                            val dRound = (measuredDown * 10).toInt() / 10.0
                                            Text(
                                                text = "↓ ${dRound} MB/s",
                                                fontSize = 9.5.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = Color(0xFFFFB300)
                                            )
                                        }
                                        // Upload
                                        if (measuredUp != null && measuredUp > 0.0) {
                                            val uRound = (measuredUp * 10).toInt() / 10.0
                                            Text(
                                                text = "↑ ${uRound} MB/s",
                                                fontSize = 9.5.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = colors.skyBlue
                                            )
                                        }
                                    }
                                }

                                // Right: Name & Protocol
                                Column(horizontalAlignment = Alignment.End) {
                                    Text(
                                        text = node.remark,
                                        fontSize = 11.5.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = if (isSelected) colors.skyBlue else colors.textPrimary,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                    Text(
                                        text = "${node.protocol.uppercase()} • ${(node.panelName ?: "سرور ابری")}",
                                        fontSize = 8.5.sp,
                                        color = colors.textMuted
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Action Button: Start Speed Test
                Button(
                    onClick = {
                        if (isTesting) {
                            isTesting = false
                        } else {
                            coroutineScope.launch {
                                isTesting = true
                                for ((idx, node) in testList.withIndex()) {
                                    if (!isTesting) break
                                    activeTestingIndex = idx
                                    testingStage = "دانلود..."
                                    val down = com.asanvpn.app.service.PingTester.measureDownloadSpeed(node, selectedPayloadMB)
                                    if (down != null) {
                                        node.downloadSpeedMBs = down
                                        testList = testList.map { if (it.remark == node.remark) it.copy(downloadSpeedMBs = down) else it }
                                        onNodeUpdated(node)
                                    }

                                    testingStage = "آپلود..."
                                    val up = com.asanvpn.app.service.PingTester.measureUploadSpeed(node, selectedPayloadMB)
                                    if (up != null) {
                                        node.uploadSpeedMBs = up
                                        testList = testList.map { if (it.remark == node.remark) it.copy(uploadSpeedMBs = up) else it }
                                        onNodeUpdated(node)
                                    }
                                }
                                isTesting = false
                                activeTestingIndex = -1
                                testingStage = ""
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth().height(42.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isTesting) colors.coralRed else colors.skyBlue,
                        contentColor = Color.White
                    )
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(
                            imageVector = if (isTesting) Icons.Default.Stop else Icons.Default.PlayArrow,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Text(
                            text = if (isTesting) "توقف سنجش سرعت" else "شروع تست سرعت (دانلود و آپلود)",
                            fontSize = 12.5.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}
