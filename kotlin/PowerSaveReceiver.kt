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
                context.registerReceiver(instance, filter)
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

    private fun updatePowerSaveState(context: Context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                val powerManager = context.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return
                val isPowerSaveMode = powerManager.isPowerSaveMode

                val liteModeClass = Class.forName("org.telegram.messenger.LiteMode")
                try {
                    val setLevelMethod = liteModeClass.getDeclaredMethod("setPowerSaverLevel", Integer.TYPE)
                    setLevelMethod.isAccessible = true
                    setLevelMethod.invoke(null, if (isPowerSaveMode) 100 else 0)
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
