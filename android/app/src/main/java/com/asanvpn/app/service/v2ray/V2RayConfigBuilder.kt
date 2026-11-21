package com.asanvpn.app.service.v2ray

import com.asanvpn.app.data.models.VpnNode
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import java.net.URLDecoder

object V2RayConfigBuilder {

    fun buildConfig(node: VpnNode): String {
        val root = JsonObject()

        // 1. Stats & Policy
        val stats = JsonObject()
        root.add("stats", stats)

        val log = JsonObject().apply {
            addProperty("loglevel", "warning")
        }
        root.add("log", log)

        val policy = JsonObject().apply {
            val levels = JsonObject().apply {
                val level8 = JsonObject().apply {
                    addProperty("handshake", 4)
                    addProperty("connIdle", 300)
                    addProperty("uplinkOnly", 1)
                    addProperty("downlinkOnly", 1)
                    addProperty("bufferSize", 10240) // 10MB streaming buffer prevents video/audio starvation
                }
                add("8", level8)
            }
            add("levels", levels)
            val system = JsonObject().apply {
                addProperty("statsOutboundUplink", true)
                addProperty("statsOutboundDownlink", true)
            }
            add("system", system)
        }
        root.add("policy", policy)

        // 2. Inbounds: tun + socks-in + http-in
        val inbounds = JsonArray().apply {
            // TUN Inbound (bound to xray.tun.fd in libv2ray)
            add(JsonObject().apply {
                addProperty("tag", "tun")
                addProperty("protocol", "tun")
                add("settings", JsonObject().apply {
                    addProperty("name", "xray0")
                    addProperty("MTU", 1400) // 1400 MTU prevents packet fragmentation on Iranian cellular LTE (MCI/Irancell)
                    addProperty("userLevel", 8)
                })
                add("sniffing", JsonObject().apply {
                    addProperty("enabled", true)
                    addProperty("routeOnly", true)
                    val destOverride = JsonArray().apply {
                        add("http")
                        add("tls")
                    }
                    add("destOverride", destOverride)
                })
            })

            // Local Socks5 Inbound for local app/browser fallback
            add(JsonObject().apply {
                addProperty("tag", "socks-in")
                addProperty("port", 10808)
                addProperty("listen", "127.0.0.1")
                addProperty("protocol", "socks")
                add("settings", JsonObject().apply {
                    addProperty("auth", "noauth")
                    addProperty("udp", true)
                    addProperty("userLevel", 8)
                })
                add("sniffing", JsonObject().apply {
                    addProperty("enabled", true)
                    addProperty("routeOnly", true)
                    val destOverride = JsonArray().apply {
                        add("http")
                        add("tls")
                    }
                    add("destOverride", destOverride)
                })
            })

            // Local HTTP Inbound
            add(JsonObject().apply {
                addProperty("tag", "http-in")
                addProperty("port", 10809)
                addProperty("listen", "127.0.0.1")
                addProperty("protocol", "http")
                add("settings", JsonObject().apply {
                    addProperty("auth", "noauth")
                })
            })
        }
        root.add("inbounds", inbounds)

        // 3. Outbounds: proxy + dns-out + direct + block
        val outbounds = JsonArray()
        val proxyOutbound = buildProxyOutbound(node)
        outbounds.add(proxyOutbound)

        // DNS outbound
        outbounds.add(JsonObject().apply {
            addProperty("tag", "dns-out")
            addProperty("protocol", "dns")
        })

        // Direct outbound
        outbounds.add(JsonObject().apply {
            addProperty("tag", "direct")
            addProperty("protocol", "freedom")
            add("settings", JsonObject().apply {
                addProperty("domainStrategy", "UseIP")
            })
            add("streamSettings", JsonObject().apply {
                add("sockopt", JsonObject().apply {
                    addProperty("domainStrategy", "UseIP")
                })
            })
        })

        // Block outbound
        outbounds.add(JsonObject().apply {
            addProperty("tag", "block")
            addProperty("protocol", "blackhole")
            add("settings", JsonObject().apply {
                add("response", JsonObject().apply {
                    addProperty("type", "none")
                })
            })
        })
        root.add("outbounds", outbounds)

        // 4. DNS: Fast standard UDP & DoH resolvers routed through proxy
        val dns = JsonObject().apply {
            addProperty("queryStrategy", "UseIPv4")
            val servers = JsonArray().apply {
                add("1.1.1.1")
                add("8.8.8.8")
            }
            add("servers", servers)
        }
        root.add("dns", dns)

        // 5. Routing: AsIs strategy matching v2rayNG (prevents blocking DNS queries on MCI/Irancell)
        val routing = JsonObject().apply {
            addProperty("domainStrategy", "AsIs")
            val rules = JsonArray().apply {
                // Rule 0: Hijack port 53 DNS queries to internal DNS engine (only from inbound tunnels)
                add(JsonObject().apply {
                    addProperty("type", "field")
                    addProperty("outboundTag", "dns-out")
                    val inboundsArr = JsonArray().apply {
                        add("tun")
                        add("socks-in")
                    }
                    add("inboundTag", inboundsArr)
                    addProperty("port", "53")
                })

                // Rule 1: Direct Iranian domains (Chocolate4Iran geosite rules)
                add(JsonObject().apply {
                    addProperty("type", "field")
                    addProperty("outboundTag", "direct")
                    val domainArr = JsonArray().apply {
                        add("geosite:category-ir")
                        add("domain:ir")
                    }
                    add("domain", domainArr)
                })

                // Rule 2: Direct private LAN & Iran IP ranges (Chocolate4Iran geoip rules)
                add(JsonObject().apply {
                    addProperty("type", "field")
                    addProperty("outboundTag", "direct")
                    val ipArr = JsonArray().apply {
                        add("geoip:private")
                        add("geoip:ir")
                    }
                    add("ip", ipArr)
                })

                // Rule 3: All other TCP & UDP -> proxy
                add(JsonObject().apply {
                    addProperty("type", "field")
                    addProperty("outboundTag", "proxy")
                    addProperty("network", "tcp,udp")
                })
            }
            add("rules", rules)
        }
        root.add("routing", routing)

        return root.toString()
    }

    /**
     * Builds lightweight config without TUN for testing outbound delay with Libv2ray.measureOutboundDelay
     */
    fun buildTestConfig(node: VpnNode): String {
        val root = JsonObject()

        val log = JsonObject().apply {
            addProperty("loglevel", "none")
        }
        root.add("log", log)

        val outbounds = JsonArray()
        outbounds.add(buildProxyOutbound(node))
        outbounds.add(JsonObject().apply {
            addProperty("tag", "direct")
            addProperty("protocol", "freedom")
        })
        root.add("outbounds", outbounds)

        val dns = JsonObject().apply {
            addProperty("queryStrategy", "UseIPv4")
            val servers = JsonArray().apply {
                add("1.1.1.1")
                add("8.8.8.8")
            }
            add("servers", servers)
        }
        root.add("dns", dns)

        return root.toString()
    }

    private fun parseRawQueryParams(rawLink: String?): Map<String, String> {
        if (rawLink.isNullOrBlank() || !rawLink.contains("?")) return emptyMap()
        val queryPart = rawLink.substringAfter("?").substringBefore("#")
        val map = mutableMapOf<String, String>()
        queryPart.split("&").forEach { param ->
            val parts = param.split("=", limit = 2)
            if (parts.isNotEmpty()) {
                val key = parts[0]
                val value = if (parts.size > 1) {
                    try { URLDecoder.decode(parts[1], "UTF-8") } catch (_: Exception) { parts[1] }
                } else ""
                map[key] = value
            }
        }
        return map
    }

    private fun buildProxyOutbound(node: VpnNode): JsonObject {
        val outbound = JsonObject()
        val proto = node.protocol.lowercase()
        val isHysteria = proto in listOf("hysteria", "hysteria2", "hy2")
        outbound.addProperty("tag", "proxy")
        outbound.addProperty("protocol", if (isHysteria) "hysteria" else proto)

        val rawParams = parseRawQueryParams(node.rawLink)

        val settings = JsonObject()
        val streamSettings = JsonObject()

        // Resolve fields with direct raw link precedence to preserve 100% parameter fidelity
        val pbk = rawParams["pbk"] ?: node.pbk
        val sid = rawParams["sid"] ?: node.sid
        val spx = rawParams["spx"] ?: node.spx
        val fp = rawParams["fp"] ?: node.fingerprint ?: "chrome"
        val rawSec = rawParams["security"] ?: node.security
        val sec = if (isHysteria) "tls" else if (!pbk.isNullOrBlank()) "reality" else (rawSec?.lowercase() ?: "none")

        val rawType = rawParams["type"] ?: node.type
        val net = if (isHysteria) "hysteria" else if (rawType.isNullOrEmpty()) "tcp" else rawType.lowercase()
        val headerType = rawParams["headerType"] ?: node.headerType ?: "none"
        val rawSni = rawParams["sni"] ?: node.sni
        val rawHost = rawParams["host"] ?: node.hostHeader ?: rawSni ?: node.server
        val rawPath = rawParams["path"] ?: node.path ?: "/"
        val rawMode = rawParams["mode"] ?: node.mode ?: "auto"
        val rawFlow = rawParams["flow"] ?: node.flow
        val rawEnc = rawParams["encryption"] ?: node.encryption ?: "none"

        streamSettings.addProperty("network", net)
        streamSettings.addProperty("security", sec)

        when {
            isHysteria -> {
                settings.addProperty("version", 2)
                settings.addProperty("address", node.server)
                settings.addProperty("port", node.port)

                val hysteriaSettings = JsonObject().apply {
                    addProperty("version", 2)
                    addProperty("auth", node.uuid ?: node.password ?: "")
                    addProperty("udpIdleTimeout", 60)
                }
                streamSettings.add("hysteriaSettings", hysteriaSettings)
            }
            proto == "vless" -> {
                val vnext = JsonArray()
                val serverObj = JsonObject()
                serverObj.addProperty("address", node.server)
                serverObj.addProperty("port", node.port)

                val users = JsonArray()
                val user = JsonObject()
                user.addProperty("id", node.uuid ?: "")
                user.addProperty("encryption", rawEnc)
                val isVisionCompatible = (sec == "tls" || sec == "reality") && (net == "tcp")
                if (!rawFlow.isNullOrBlank() && isVisionCompatible) {
                    user.addProperty("flow", rawFlow)
                }
                users.add(user)
                serverObj.add("users", users)
                vnext.add(serverObj)
                settings.add("vnext", vnext)
            }
            proto == "vmess" -> {
                val vnext = JsonArray()
                val serverObj = JsonObject()
                serverObj.addProperty("address", node.server)
                serverObj.addProperty("port", node.port)

                val users = JsonArray()
                val user = JsonObject()
                user.addProperty("id", node.uuid ?: "")
                user.addProperty("alterId", 0)
                user.addProperty("security", "auto")
                users.add(user)
                serverObj.add("users", users)
                vnext.add(serverObj)
                settings.add("vnext", vnext)
            }
            proto == "trojan" -> {
                val servers = JsonArray()
                val serverObj = JsonObject()
                serverObj.addProperty("address", node.server)
                serverObj.addProperty("port", node.port)
                serverObj.addProperty("password", node.password ?: "")
                servers.add(serverObj)
                settings.add("servers", servers)
            }
            proto == "shadowsocks" -> {
                val servers = JsonArray()
                val serverObj = JsonObject()
                serverObj.addProperty("address", node.server)
                serverObj.addProperty("port", node.port)
                serverObj.addProperty("method", node.cipher ?: "chacha20-ietf-poly1305")
                serverObj.addProperty("password", node.password ?: "")
                servers.add(serverObj)
                settings.add("servers", servers)
            }
        }
        outbound.add("settings", settings)

        // Security: TLS or Reality
        if (sec == "tls") {
            val tls = JsonObject()
            val serverName = if (!rawSni.isNullOrBlank()) rawSni else node.server
            tls.addProperty("serverName", serverName)
            if (!isHysteria) {
                tls.addProperty("allowInsecure", false)
                val alpn = JsonArray()
                val rawAlpn = rawParams["alpn"]?.split(",") ?: node.alpn
                if (!rawAlpn.isNullOrEmpty()) {
                    rawAlpn.forEach { alpn.add(it.trim()) }
                } else {
                    alpn.add("http/1.1")
                }
                tls.add("alpn", alpn)
            }
            streamSettings.add("tlsSettings", tls)
        } else if (sec == "reality") {
            val reality = JsonObject()
            val serverName = if (!rawSni.isNullOrBlank() && !rawSni.matches(Regex("""^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"""))) {
                rawSni
            } else if (!node.server.matches(Regex("""^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"""))) {
                node.server
            } else {
                "play.google.com"
            }
            reality.addProperty("serverName", serverName)
            reality.addProperty("fingerprint", fp)
            reality.addProperty("publicKey", pbk ?: "")
            reality.addProperty("shortId", sid ?: "")
            reality.addProperty("spiderX", spx ?: "")
            streamSettings.add("realitySettings", reality)
        }

        // Network: ws / grpc / xhttp / tcp
        if (net == "ws") {
            val ws = JsonObject()
            ws.addProperty("path", rawPath)
            val headers = JsonObject()
            headers.addProperty("Host", rawHost)
            ws.add("headers", headers)
            streamSettings.add("wsSettings", ws)
        } else if (net == "grpc") {
            val grpc = JsonObject()
            val serviceName = rawParams["serviceName"] ?: node.serviceName ?: rawPath
            grpc.addProperty("serviceName", serviceName)
            grpc.addProperty("multiMode", true)
            streamSettings.add("grpcSettings", grpc)
        } else if (net == "xhttp" || net == "splithttp") {
            val xhttp = JsonObject()
            xhttp.addProperty("path", rawPath)
            xhttp.addProperty("host", rawHost)
            xhttp.addProperty("mode", rawMode)
            streamSettings.add("xhttpSettings", xhttp)
        } else if (net == "tcp" && headerType.lowercase() == "http") {
            val tcp = JsonObject()
            val header = JsonObject()
            header.addProperty("type", "http")
            val request = JsonObject()
            request.addProperty("path", rawPath)
            val headers = JsonObject()
            headers.addProperty("Host", rawHost)
            request.add("headers", headers)
            header.add("request", request)
            tcp.add("header", header)
            streamSettings.add("tcpSettings", tcp)
        }

        // Streaming latency & throughput optimization: disable Nagle's delay, enable TCP keepalive
        val sockopt = JsonObject().apply {
            addProperty("tcpNoDelay", true)
            addProperty("tcpKeepAliveInterval", 15)
        }
        streamSettings.add("sockopt", sockopt)

        outbound.add("streamSettings", streamSettings)
        return outbound
    }
}
