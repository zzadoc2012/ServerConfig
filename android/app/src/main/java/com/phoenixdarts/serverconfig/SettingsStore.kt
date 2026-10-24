package com.phoenixdarts.serverconfig

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys

class SettingsStore(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        "serverconfig_accounts",
        MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC),
        context,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun account(live: Boolean): Account {
        val prefix = if (live) "live" else "test"
        val defaultAddress = if (live) {
            "https://admin.phoenixdarts.com/"
        } else {
            "https://test-admin.phoenixdarts.com/"
        }
        return Account(
            address = prefs.getString("${prefix}_address", defaultAddress).orEmpty(),
            userId = prefs.getString("${prefix}_id", "").orEmpty(),
            password = prefs.getString("${prefix}_password", "").orEmpty(),
        )
    }

    fun save(
        testAddress: String,
        testId: String,
        testPassword: String,
        liveAddress: String,
        liveId: String,
        livePassword: String,
    ) {
        prefs.edit()
            .putString("test_address", testAddress.trim())
            .putString("test_id", testId.trim())
            .putString("test_password", testPassword)
            .putString("live_address", liveAddress.trim())
            .putString("live_id", liveId.trim())
            .putString("live_password", livePassword)
            .apply()
    }
}
