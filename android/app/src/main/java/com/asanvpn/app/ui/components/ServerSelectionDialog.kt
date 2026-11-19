package com.asanvpn.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
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

@Composable
fun ServerSelectionDialog(
    availableNodes: List<VpnNode>,
    currentSelectedRemark: String?,
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

    // Identify highest priority panel (lowest integer priority value)
    val topPriority = remember(availableNodes) {
        availableNodes.mapNotNull { it.panelPriority }.minOrNull() ?: 1
    }

    // In manual mode: strictly filter to only nodes belonging to the top priority panel!
    val candidateNodes = remember(availableNodes, topPriority) {
        val top = availableNodes.filter { (it.panelPriority ?: 1) == topPriority }
        if (top.isNotEmpty()) top else availableNodes
    }

    // Automatically trigger fresh ping if no candidate node has a measured latency
    LaunchedEffect(candidateNodes) {
        val hasAnyPing = candidateNodes.any {
            it.latencyMs > 0 || (com.asanvpn.app.data.NodeMetricsCache.getLatency(it) ?: -1L) > 0
        }
        if (!hasAnyPing && onRefreshPing != null && !isPinging) {
            onRefreshPing()
        }
    }

    val topPanelName = remember(candidateNodes) {
        candidateNodes.firstOrNull()?.panelName ?: "پنل اولویت ۱"
    }

    val filteredNodes = remember(candidateNodes, searchQuery) {
        if (searchQuery.isBlank()) {
            candidateNodes
        } else {
            val q = searchQuery.trim().lowercase()
            candidateNodes.filter { node ->
                node.remark.lowercase().contains(q) ||
                (node.panelName?.lowercase()?.contains(q) == true) ||
                node.server.lowercase().contains(q)
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
                            text = "انتخاب سرور ($topPanelName)",
                            fontSize = if (isSmallScreen) 13.5.sp else 15.sp,
                            fontWeight = FontWeight.Black,
                            color = colors.textPrimary
                        )
                        Text(
                            text = "اولویت ۱ • ${filteredNodes.size} سرور در دسترس",
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
                    }
                    Text(
                        text = "سرورهای $topPanelName (اولویت ۱)",
                        fontSize = 11.5.sp,
                        fontWeight = FontWeight.Bold,
                        color = colors.textSecondary
                    )
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
                            key = { index, node -> "${index}_${node.server}_${node.port}_${node.remark.hashCode()}" }
                        ) { index, node ->
                            val rawRemark = node.remark ?: ""
                            val remarkSafe = if (rawRemark.isNotBlank()) rawRemark else "سرور ${index + 1}"
                            val isSelected = !isAutoServerMode && (remarkSafe == currentSelectedRemark || rawRemark == currentSelectedRemark)

                            val measuredLatency = if (node.latencyMs > 0) {
                                node.latencyMs
                            } else {
                                com.asanvpn.app.data.NodeMetricsCache.getLatency(node) ?: -1L
                            }

                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .luxuryCushion(shape = RoundedCornerShape(18.dp), elevation = 3.dp)
                                    .border(
                                        width = if (isSelected) 1.5.dp else 0.dp,
                                        color = if (isSelected) colors.skyBlue else Color.Transparent,
                                        shape = RoundedCornerShape(18.dp)
                                    )
                                    .clickable { onSelectNode(node) }
                                    .padding(
                                        horizontal = if (isSmallScreen) 10.dp else 12.dp,
                                        vertical = if (isSmallScreen) 7.dp else 10.dp
                                    )
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    // Left: Latency Badge + Radio indicator
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        RadioButton(
                                            selected = isSelected,
                                            onClick = { onSelectNode(node) },
                                            colors = RadioButtonDefaults.colors(selectedColor = colors.skyBlue)
                                        )

                                        Box(
                                            modifier = Modifier
                                                .luxuryWell(shape = RoundedCornerShape(12.dp))
                                                .padding(horizontal = 7.dp, vertical = 3.5.dp)
                                        ) {
                                            if (measuredLatency > 0) {
                                                val badgeColor = when {
                                                    measuredLatency < 160 -> colors.jadeGreen
                                                    measuredLatency < 300 -> colors.skyBlue
                                                    else -> Color(0xFFFFA726)
                                                }
                                                Text(
                                                    text = "$measuredLatency ms",
                                                    fontSize = 10.5.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = badgeColor
                                                )
                                            } else {
                                                Text(
                                                    text = "-- ms",
                                                    fontSize = 10.sp,
                                                    fontWeight = FontWeight.Medium,
                                                    color = colors.textMuted
                                                )
                                            }
                                        }
                                    }

                                    // Right: Remark Name + Panel Badge
                                    Column(
                                        horizontalAlignment = Alignment.End,
                                        modifier = Modifier.weight(1f).padding(start = 8.dp)
                                    ) {
                                        Text(
                                            text = remarkSafe,
                                            fontSize = 12.5.sp,
                                            fontWeight = FontWeight.ExtraBold,
                                            color = if (isSelected) colors.skyBlue else colors.textPrimary,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                            textAlign = TextAlign.Right
                                        )

                                        Spacer(modifier = Modifier.height(3.dp))

                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            val panelName = (node.panelName ?: "").ifBlank { "سرور ابری" }
                                            Box(
                                                modifier = Modifier
                                                    .clip(RoundedCornerShape(6.dp))
                                                    .background(colors.skyBlue.copy(alpha = 0.12f))
                                                    .padding(horizontal = 6.dp, vertical = 2.dp)
                                            ) {
                                                Text(
                                                    text = panelName,
                                                    fontSize = 9.5.sp,
                                                    fontWeight = FontWeight.SemiBold,
                                                    color = colors.skyBlue
                                                )
                                            }

                                            val proto = (node.protocol ?: "VLESS").uppercase()
                                            val transport = (node.type ?: "TCP").uppercase()
                                            Text(
                                                text = "$proto • $transport",
                                                fontSize = 9.5.sp,
                                                color = colors.textMuted
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
