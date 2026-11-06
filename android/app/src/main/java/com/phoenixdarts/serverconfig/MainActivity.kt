package com.phoenixdarts.serverconfig

import android.content.ClipData
import android.content.ClipboardManager
import android.os.Bundle
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.phoenixdarts.serverconfig.databinding.ActivityMainBinding
import com.phoenixdarts.serverconfig.databinding.DialogAddConfigBinding
import com.phoenixdarts.serverconfig.databinding.DialogSettingsBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var assetsRepo: AssetRepository
    private lateinit var store: SettingsStore
    private var currentMac: String = ""
    private var running = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        assetsRepo = AssetRepository(this)
        store = SettingsStore(this)
        setupMachines()
        binding.resetButton.setOnClickListener { onReset() }
        binding.settingsButton.setOnClickListener { openSettings() }
        binding.copyMacButton.setOnClickListener { copyMac() }
        binding.addConfigButton.setOnClickListener { onAddConfig() }
        binding.runButton.setOnClickListener { onRun() }
        binding.machineSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                onMachineChanged()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        appendLog("내장 머신 목록을 읽었습니다. (${assetsRepo.machines.size}대)")
        appendLog("내장 엑셀 컨피그를 읽었습니다.")
    }

    private fun setupMachines() {
        val labels = mutableListOf(getString(R.string.machine_placeholder))
        labels.addAll(assetsRepo.machines.map { it.label() })
        binding.machineSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, labels)
        fillConfigs(null)
        setResetEnabled()
    }

    private fun selectedMachine(): Machine? {
        val index = binding.machineSpinner.selectedItemPosition - 1
        return assetsRepo.machines.getOrNull(index)
    }

    private fun onMachineChanged() {
        val machine = selectedMachine()
        binding.typeVss.isChecked = false
        binding.typeS4.isChecked = false
        binding.typeVsx.isChecked = false
        binding.typeMax.isChecked = false
        currentMac = ""
        if (machine == null) {
            binding.machineInfo.text = "위치: -"
            binding.copyMacButton.isEnabled = false
            fillConfigs(null)
            setResetEnabled()
            return
        }
        when (machine.checkboxType()) {
            "VSS/VSP" -> binding.typeVss.isChecked = true
            "S4" -> binding.typeS4.isChecked = true
            "VSX" -> binding.typeVsx.isChecked = true
            "MAX" -> binding.typeMax.isChecked = true
        }
        currentMac = machine.mac.trim()
        val macText = currentMac.ifBlank { "(MAC 없음)" }
        val location = machine.location.ifBlank { "-" }
        binding.machineInfo.text = "위치: $location  |  IP: ${machine.ip}  |  MAC: $macText"
        binding.copyMacButton.isEnabled = currentMac.isNotBlank()
        fillConfigs(machine.excelColumn())
        setResetEnabled()
    }

    private fun fillConfigs(column: String?, keepName: String? = null) {
        val names = mutableListOf(getString(R.string.config_placeholder))
        if (column != null) {
            names.addAll(assetsRepo.configsFor(column).map { it.name })
        }
        binding.configSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, names)
        val keepIndex = keepName?.let { names.indexOf(it) } ?: -1
        binding.configSpinner.setSelection(if (keepIndex > 0) keepIndex else 0)
        binding.configSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                refreshPreview()
            }

            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
        }
        refreshPreview()
    }

    private fun refreshPreview() {
        val machine = selectedMachine()
        val position = binding.configSpinner.selectedItemPosition
        if (machine == null || position <= 0) {
            binding.preview.text = ""
            return
        }
        val name = binding.configSpinner.selectedItem?.toString().orEmpty()
        val item = assetsRepo.configs.firstOrNull { it.name == name }
        binding.preview.text = item?.valueFor(machine.excelColumn()).orEmpty()
    }

    private fun copyMac() {
        if (currentMac.isBlank()) {
            Toast.makeText(this, "복사할 MAC이 없습니다.", Toast.LENGTH_SHORT).show()
            return
        }
        val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("mac", currentMac))
        appendLog("MAC 주소를 클립보드에 복사했습니다.")
    }

    private fun openSettings() {
        val dialogBinding = DialogSettingsBinding.inflate(layoutInflater)
        val test = store.account(false)
        val live = store.account(true)
        dialogBinding.testAddress.setText(test.address)
        dialogBinding.testId.setText(test.userId)
        dialogBinding.testPassword.setText(test.password)
        dialogBinding.liveAddress.setText(live.address)
        dialogBinding.liveId.setText(live.userId)
        dialogBinding.livePassword.setText(live.password)
        AlertDialog.Builder(this)
            .setTitle("계정 설정")
            .setView(dialogBinding.root)
            .setPositiveButton("저장") { _, _ ->
                if (dialogBinding.testId.text.toString().isBlank()) {
                    Toast.makeText(this, "테스트 어드민 아이디를 입력하세요.", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                store.save(
                    dialogBinding.testAddress.text.toString(),
                    dialogBinding.testId.text.toString(),
                    dialogBinding.testPassword.text.toString(),
                    dialogBinding.liveAddress.text.toString(),
                    dialogBinding.liveId.text.toString(),
                    dialogBinding.livePassword.text.toString(),
                )
                Toast.makeText(this, "저장했습니다.", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun onAddConfig() {
        val dialogBinding = DialogAddConfigBinding.inflate(layoutInflater)
        AlertDialog.Builder(this)
            .setTitle("컨피그 추가")
            .setView(dialogBinding.root)
            .setPositiveButton("저장") { _, _ ->
                val name = dialogBinding.configName.text.toString()
                val values = mapOf(
                    "VSS/VSP" to dialogBinding.valueVss.text.toString(),
                    "S4" to dialogBinding.valueS4.text.toString(),
                    "VSX" to dialogBinding.valueVsx.text.toString(),
                    "MAX" to dialogBinding.valueMax.text.toString(),
                )
                try {
                    assetsRepo.add(name, values)
                } catch (exc: Exception) {
                    Toast.makeText(this, exc.message ?: "저장하지 못했습니다.", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                appendLog("컨피그를 추가했습니다: $name")
                val column = selectedMachine()?.excelColumn()
                fillConfigs(column, name)
                if (column != null && assetsRepo.configsFor(column).none { it.name == name }) {
                    Toast.makeText(this, "저장했습니다. 선택한 머신 타입 열이 비어 있어 목록에는 보이지 않습니다.", Toast.LENGTH_LONG).show()
                }
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun onReset() {
        val machine = selectedMachine() ?: return
        AlertDialog.Builder(this)
            .setTitle("컨피그 초기화")
            .setMessage("Cam:Use:Online=1 을 제외하고 모든 컨피그를 삭제합니다.")
            .setPositiveButton("확인") { _, _ ->
                startJob(machine, ConfigMerge.RESET_KEEP_LINE, replace = true, action = "컨피그 초기화")
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun onRun() {
        val machine = selectedMachine()
        if (machine == null) {
            Toast.makeText(this, "머신을 선택하세요.", Toast.LENGTH_SHORT).show()
            return
        }
        val position = binding.configSpinner.selectedItemPosition
        if (position <= 0) {
            Toast.makeText(this, "적용할 컨피그를 선택하세요.", Toast.LENGTH_SHORT).show()
            return
        }
        val configName = binding.configSpinner.selectedItem.toString()
        val configText = assetsRepo.configs.first { it.name == configName }.valueFor(machine.excelColumn())
        if (configText.isBlank()) {
            Toast.makeText(this, "선택한 컨피그 셀이 비어 있습니다.", Toast.LENGTH_SHORT).show()
            return
        }
        startJob(machine, configText, replace = false, action = "컨피그 적용")
    }

    private fun startJob(machine: Machine, configText: String, replace: Boolean, action: String) {
        if (running) {
            Toast.makeText(this, "이미 작업이 진행 중입니다.", Toast.LENGTH_SHORT).show()
            return
        }
        if (machine.mac.isBlank()) {
            Toast.makeText(this, "${machine.label()}의 MAC이 없습니다.", Toast.LENGTH_SHORT).show()
            return
        }
        val live = binding.envLive.isChecked
        val account = store.account(live)
        if (account.userId.isBlank() || account.password.isBlank()) {
            Toast.makeText(this, "설정에서 선택한 환경의 아이디와 비밀번호를 저장하세요.", Toast.LENGTH_SHORT).show()
            return
        }
        if (account.address.isBlank()) {
            Toast.makeText(this, "어드민 주소가 없습니다.", Toast.LENGTH_SHORT).show()
            return
        }
        if (live) {
            AlertDialog.Builder(this)
                .setTitle("라이브 환경 확인")
                .setMessage("라이브 어드민에 접속하여 ${action}합니다.\n주소: ${account.address}\n머신: ${machine.label()}\n계속할까요?")
                .setPositiveButton("예") { _, _ -> startRun(account, machine, configText, replace) }
                .setNegativeButton("아니오") { _, _ -> appendLog("라이브 실행을 취소했습니다.") }
                .show()
            return
        }
        startRun(account, machine, configText, replace)
    }

    private fun startRun(account: Account, machine: Machine, configText: String, replace: Boolean) {
        running = true
        binding.runButton.isEnabled = false
        setResetEnabled()
        binding.logView.text = ""
        appendLog("머신: ${machine.label()}")
        appendLog("환경: " + if (binding.envLive.isChecked) "라이브 어드민" else "테스트 어드민")
        if (replace) appendLog("컨피그 초기화: ${ConfigMerge.RESET_KEEP_LINE} 만 남깁니다.")
        lifecycleScope.launch {
            try {
                withContext(Dispatchers.IO) {
                    AdminClient().applyConfig(
                        account.address,
                        account.userId,
                        account.password,
                        machine.mac,
                        configText,
                        { message -> runOnUiThread { appendLog(message) } },
                        replace,
                    )
                }
                Toast.makeText(this@MainActivity, "작업을 완료했습니다.", Toast.LENGTH_SHORT).show()
            } catch (exc: Exception) {
                appendLog(exc.message ?: exc.toString())
                Toast.makeText(this@MainActivity, exc.message ?: "오류", Toast.LENGTH_LONG).show()
            } finally {
                running = false
                binding.runButton.isEnabled = true
                setResetEnabled()
            }
        }
    }

    private fun setResetEnabled() {
        binding.resetButton.isEnabled = selectedMachine() != null && !running
    }

    private fun appendLog(message: String) {
        val current = binding.logView.text?.toString().orEmpty()
        binding.logView.text = if (current.isBlank()) message else current + "\n" + message
    }
}
