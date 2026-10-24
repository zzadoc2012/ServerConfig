package com.phoenixdarts.serverconfig

object ConfigMerge {
    fun normalize(text: String): String {
        val cleaned = text.replace("\r\n", "\n").split("\n").map { it.trim() }.toMutableList()
        while (cleaned.isNotEmpty() && cleaned.first() == "") cleaned.removeAt(0)
        while (cleaned.isNotEmpty() && cleaned.last() == "") cleaned.removeAt(cleaned.lastIndex)
        return cleaned.joinToString("\n")
    }

    fun merge(existing: String, incoming: String): String {
        val commandLines = normalize(incoming).split("\n").filter { it.isNotBlank() }
        if (commandLines.isEmpty()) return existing
        val keys = commandLines.mapNotNull { lineKey(it) }.toSet()
        val kept = existing.replace("\r\n", "\n").split("\n").filter { line ->
            val key = lineKey(line)
            key == null || key !in keys
        }.toMutableList()
        while (kept.isNotEmpty() && kept.last() == "") kept.removeAt(kept.lastIndex)
        val body = if (kept.isEmpty()) commandLines else kept + commandLines
        return body.joinToString("\n") + "\n"
    }

    private fun lineKey(line: String): String? {
        val text = line.trim()
        if (text.isEmpty() || '=' !in text) return null
        return text.split('=', limit = 2)[0].trim()
    }
}
