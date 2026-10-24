package com.phoenixdarts.serverconfig

import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.FormBody
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AdminException(message: String) : RuntimeException(message)

class AdminClient {
    private val cookies = MemoryCookieJar()
    private val http = OkHttpClient.Builder()
        .cookieJar(cookies)
        .followRedirects(true)
        .followSslRedirects(true)
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    fun applyConfig(
        baseUrl: String,
        userId: String,
        password: String,
        mac: String,
        configText: String,
        log: (String) -> Unit,
    ) {
        val root = normalizeBase(baseUrl)
        log("1/8 접속을 준비합니다.")
        log("2/8 어드민에 접속합니다.")
        get(root)
        log("3/8 로그인합니다.")
        login(root, userId, password)
        log("4/8 로그인했습니다.")
        log("5/8 Machine 페이지로 이동합니다.")
        get("${root}machine/log_control")
        log("6/8 머신을 검색합니다.")
        val found = search(root, mac)
        val seq = found.optString("machine_seq")
        if (seq.isBlank()) throw AdminException("검색 결과에서 machine_seq를 찾지 못했습니다.")
        val existing = found.optString("config_memo")
        val merged = ConfigMerge.merge(existing, configText)
        log("7/8 선택한 설정을 저장합니다.")
        save(root, seq, merged)
        log("8/8 작업을 완료했습니다.")
    }

    private fun login(root: String, userId: String, password: String) {
        val body = FormBody.Builder()
            .add("admin_id", userId)
            .add("passwd", password)
            .build()
        val response = post("${root}login/loginok", body)
        val text = response.lowercase()
        if (text.contains("id=\"admin_id\"") || text.contains("name=\"admin_id\"")) {
            throw AdminException("로그인에 실패했거나 추가 인증이 필요합니다.")
        }
    }

    private fun search(root: String, mac: String): JSONObject {
        val macValue = mac.replace(":", "").replace("-", "").replace(" ", "")
        val body = FormBody.Builder()
            .add("machine_no", macValue)
            .add("nationcode", "")
            .add("s_seq", "")
            .add("shopname", "")
            .add("machine_seq", "")
            .add("machineserial", "")
            .add("machine_model_code", "")
            .add("hardware_version", "0")
            .add("dealer", "")
            .add("logflag", "all")
            .add("lineflag", "all")
            .add("tunnelingflag", "all")
            .add("idcflag", "all")
            .add("list_load", "1")
            .build()
        val raw = post("${root}machine/log_control/page/1", body)
        val json = try {
            JSONObject(raw)
        } catch (_: Exception) {
            throw AdminException("search 이후 JSON을 읽지 못했습니다.")
        }
        val list = json.optJSONArray("list_data")
        if (list == null || list.length() == 0) {
            val desc = json.optString("x")
            throw AdminException("해당 MAC으로 머신을 찾지 못했습니다. $desc")
        }
        return list.getJSONObject(0)
    }

    private fun save(root: String, seq: String, text: String) {
        val body = FormBody.Builder()
            .add("txt_config_memo_$seq", text)
            .add("mode", "edit_config")
            .add("machine_seq", seq)
            .build()
        val raw = post("${root}machine/log_control_prc", body)
        val lower = raw.lowercase()
        if ("success" !in lower && !raw.trim().startsWith("{")) {
            throw AdminException("Config 저장을 확인하지 못했습니다.")
        }
        if (raw.trim().startsWith("{")) {
            val json = JSONObject(raw)
            if (json.has("error") && json.optString("error").isNotBlank()) {
                throw AdminException("Config 저장을 확인하지 못했습니다. ${json.optString("error")}")
            }
        }
    }

    private fun get(url: String): String {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", USER_AGENT)
            .build()
        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw AdminException("요청 실패: ${response.code}")
            }
            return text
        }
    }

    private fun post(url: String, body: FormBody): String {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", USER_AGENT)
            .header("X-Requested-With", "XMLHttpRequest")
            .post(body)
            .build()
        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw AdminException("요청 실패: ${response.code}")
            }
            return text
        }
    }

    private fun normalizeBase(url: String): String {
        val trimmed = if (url.endsWith("/")) url else "$url/"
        return trimmed.toHttpUrl().toString()
    }

    companion object {
        private const val USER_AGENT =
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"
    }
}

private class MemoryCookieJar : CookieJar {
    private val store = mutableListOf<Cookie>()

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        cookies.forEach { cookie ->
            store.removeAll { it.name == cookie.name && it.matches(url) }
            store.add(cookie)
        }
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        return store.filter { it.matches(url) }
    }
}
