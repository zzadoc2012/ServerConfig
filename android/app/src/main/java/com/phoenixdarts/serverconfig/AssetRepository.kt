package com.phoenixdarts.serverconfig

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

class AssetRepository(private val context: Context) {
    val machines: List<Machine> by lazy { loadMachines() }
    val configs: List<ConfigItem> by lazy { loadConfigs() }

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

    private fun loadConfigs(): List<ConfigItem> {
        val raw = context.assets.open("configs.json").bufferedReader().use { it.readText() }
        val array = JSONObject(raw).getJSONArray("configs")
        return (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            val valuesObj = obj.getJSONObject("values")
            val values = mutableMapOf<String, String>()
            valuesObj.keys().forEach { key -> values[key] = valuesObj.optString(key) }
            ConfigItem(name = obj.getString("name"), values = values)
        }
    }

    fun configsFor(column: String): List<ConfigItem> =
        configs.filter { it.valueFor(column).isNotBlank() }
}
