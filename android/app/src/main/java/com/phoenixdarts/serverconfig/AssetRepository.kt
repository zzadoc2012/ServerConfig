package com.phoenixdarts.serverconfig

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class AssetRepository(private val context: Context) {
    val machines: List<Machine> by lazy { loadMachines() }
    var configs: MutableList<ConfigItem> = mutableListOf()
        private set

    private val bundledNames: Set<String>
    private val userFile = File(context.filesDir, "user_configs.json")

    init {
        val bundled = loadJsonConfigs(context.assets.open("configs.json").bufferedReader().use { it.readText() })
        bundledNames = bundled.map { it.name }.toSet()
        configs = (bundled + loadUserConfigs()).toMutableList()
    }

    private fun loadMachines(): List<Machine> {
        val raw = context.assets.open("machines.json").bufferedReader().use { it.readText() }
        val array = JSONArray(raw)
        return (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            Machine(
                code = obj.getString("code"),
                type = obj.getString("type"),
                ip = obj.optString("ip"),
                mac = obj.optString("mac"),
                location = obj.optString("Location").trim().trim('(', ')'),
            )
        }
    }

    fun configsFor(column: String): List<ConfigItem> =
        configs.filter { it.valueFor(column).isNotBlank() }

    fun add(name: String, values: Map<String, String>) {
        val cleanedName = name.trim()
        if (cleanedName.isEmpty()) throw IllegalArgumentException("Config Name을 입력하세요.")
        if (configs.any { it.name == cleanedName }) throw IllegalArgumentException("같은 Config Name이 이미 있습니다.")
        val cleaned = TYPE_HEADERS.associateWith { ConfigMerge.normalize(values[it].orEmpty()) }
        if (cleaned.values.all { it.isBlank() }) {
            throw IllegalArgumentException("VSS/VSP, S4, VSX, MAX 중 하나 이상 입력하세요.")
        }
        configs.add(ConfigItem(cleanedName, cleaned))
        saveUserConfigs()
    }

    private fun loadUserConfigs(): List<ConfigItem> {
        if (!userFile.exists()) return emptyList()
        return loadJsonConfigs(userFile.readText(Charsets.UTF_8)).filter { it.name !in bundledNames }
    }

    private fun saveUserConfigs() {
        val extras = configs.filter { it.name !in bundledNames }
        val root = JSONObject()
        val array = JSONArray()
        extras.forEach { item ->
            val values = JSONObject()
            TYPE_HEADERS.forEach { header -> values.put(header, item.values[header].orEmpty()) }
            array.put(JSONObject().put("name", item.name).put("values", values))
        }
        root.put("configs", array)
        userFile.writeText(root.toString(), Charsets.UTF_8)
    }

    private fun loadJsonConfigs(raw: String): List<ConfigItem> {
        val array = JSONObject(raw).getJSONArray("configs")
        return (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            val valuesObj = obj.getJSONObject("values")
            val values = mutableMapOf<String, String>()
            valuesObj.keys().forEach { key -> values[key] = valuesObj.optString(key) }
            ConfigItem(name = obj.getString("name"), values = values)
        }
    }

    companion object {
        val TYPE_HEADERS = listOf("VSS/VSP", "S4", "VSX", "MAX")
    }
}
