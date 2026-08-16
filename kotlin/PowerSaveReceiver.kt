package non.feature.powersaver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.PowerManager

class PowerSaveReceiver : BroadcastReceiver() {

    companion object {
        @JvmStatic
        private var instance: PowerSaveReceiver? = null

        @JvmStatic
        fun register(context: Context) {
            if (instance == null) {
                instance = PowerSaveReceiver()
                val filter = IntentFilter().apply {
                    addAction(PowerManager.ACTION_POWER_SAVE_MODE_CHANGED)
                    addAction("miui.intent.action.POWER_SAVE_MODE_CHANGED")
                    addAction("huawei.intent.action.POWER_MODE_CHANGED_ACTION")
                }
                if (Build.VERSION.SDK_INT >= 33) {
                    context.registerReceiver(instance, filter, 2)
                } else {
                    context.registerReceiver(instance, filter)
                }
                instance?.updatePowerSaveState(context)
            }
        }

        @JvmStatic
        fun unregister(context: Context) {
            instance?.let {
                context.unregisterReceiver(it)
                instance = null
            }
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        if (PowerManager.ACTION_POWER_SAVE_MODE_CHANGED == action ||
            "miui.intent.action.POWER_SAVE_MODE_CHANGED" == action ||
            "huawei.intent.action.POWER_MODE_CHANGED_ACTION" == action) {
            updatePowerSaveState(context)
        }
    }

    private fun isPowerSaveModeActive(context: Context, powerManager: PowerManager): Boolean {
        if (powerManager.isPowerSaveMode) {
            return true
        }
        
        val resolver = context.contentResolver
        
        try {
            val miuiPowerSave = android.provider.Settings.System.getInt(resolver, "POWER_SAVE_MODE_OPEN")
            if (miuiPowerSave == 1) return true
        } catch (e: android.provider.Settings.SettingNotFoundException) {}
        
        try {
            val huaweiPowerSave = android.provider.Settings.System.getInt(resolver, "SmartModeStatus")
            if (huaweiPowerSave == 4 || huaweiPowerSave == 1) return true
        } catch (e: android.provider.Settings.SettingNotFoundException) {}
        
        try {
            val samsungPowerSave = android.provider.Settings.System.getString(resolver, "psm_switch")
            if (samsungPowerSave == "1") return true
        } catch (e: Exception) {}

        try {
            val globalPowerSave = android.provider.Settings.Global.getInt(resolver, "low_power")
            if (globalPowerSave == 1) return true
        } catch (e: android.provider.Settings.SettingNotFoundException) {}
        
        return false
    }

    private fun updatePowerSaveState(context: Context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                val powerManager = context.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return
                val isPowerSaveMode = isPowerSaveModeActive(context, powerManager)

                val liteModeClass = Class.forName("org.telegram.messenger.LiteMode")
                try {
                    val field = liteModeClass.getDeclaredField("powerSaverLevel")
                    field.isAccessible = true
                    
                    if (isPowerSaveMode) {
                        field.setInt(null, 100)
                    } else {
                        field.setInt(null, 0)
                    }
                    
                    val getValueMethod = liteModeClass.getDeclaredMethod("getValue")
                    getValueMethod.isAccessible = true
                    getValueMethod.invoke(null)
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
