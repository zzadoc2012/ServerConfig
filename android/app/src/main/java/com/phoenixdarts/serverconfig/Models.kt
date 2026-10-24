package com.phoenixdarts.serverconfig

data class Machine(
    val code: String,
    val type: String,
    val ip: String,
    val mac: String,
    val location: String,
) {
    fun label(): String {
        val base = "$type $code"
        return if (location.isBlank()) base else "$base   ($location)"
    }

    fun excelColumn(): String = when (type) {
        "VSS", "VSP", "VSS/VSP" -> "VSS/VSP"
        else -> type
    }

    fun checkboxType(): String = when (type) {
        "VSS", "VSP" -> "VSS/VSP"
        else -> type
    }
}

data class ConfigItem(
    val name: String,
    val values: Map<String, String>,
) {
    fun valueFor(column: String): String = values[column].orEmpty()
}

data class Account(
    val address: String,
    val userId: String,
    val password: String,
)
