// static/js/dynamic_accounts.js
document.addEventListener('DOMContentLoaded', function() {
    // ตัวแปรสำหรับนับจำนวนบัญชี
    let depositCount = 1;
    let withdrawalCount = 1;
    const maxAccounts = 10; // จำกัดสูงสุด 10 บัญชี

    // เพิ่มบัญชีฝาก
    document.getElementById('add-deposit-btn').addEventListener('click', function() {
        if (depositCount < maxAccounts) {
            const depositContainer = document.getElementById('deposit-container');
            const depositRows = depositContainer.querySelectorAll('.deposit-row');
            const newRow = depositRows[0].cloneNode(true);
            
            newRow.querySelector('input').value = '0';
            newRow.querySelector('.remove-deposit-btn').disabled = false;
            depositContainer.appendChild(newRow);
            depositCount++;
        } else {
            alert('สามารถเพิ่มบัญชีฝากได้สูงสุด ' + maxAccounts + ' บัญชี');
        }
    });

    // เพิ่มบัญชีถอน
    document.getElementById('add-withdrawal-btn').addEventListener('click', function() {
        if (withdrawalCount < maxAccounts) {
            const withdrawalContainer = document.getElementById('withdrawal-container');
            const withdrawalRows = withdrawalContainer.querySelectorAll('.withdrawal-row');
            const newRow = withdrawalRows[0].cloneNode(true);
            
            newRow.querySelector('input').value = '0';
            newRow.querySelector('.remove-withdrawal-btn').disabled = false;
            withdrawalContainer.appendChild(newRow);
            withdrawalCount++;
        } else {
            alert('สามารถเพิ่มบัญชีถอนได้สูงสุด ' + maxAccounts + ' บัญชี');
        }
    });

    // ลบบัญชีฝาก
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-deposit-btn')) {
            const depositRows = document.querySelectorAll('.deposit-row');
            if (depositRows.length > 1) {
                e.target.closest('.deposit-row').remove();
                depositCount--;
            }
        }

        // ลบบัญชีถอน
        if (e.target.classList.contains('remove-withdrawal-btn')) {
            const withdrawalRows = document.querySelectorAll('.withdrawal-row');
            if (withdrawalRows.length > 1) {
                e.target.closest('.withdrawal-row').remove();
                withdrawalCount--;
            }
        }
    });

    // ตรวจสอบบัญชีซ้ำ
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('bank-select')) {
            const currentValue = e.target.value;
            if (currentValue === '') return;

            const container = e.target.closest('.row').parentElement;
            const selects = container.querySelectorAll('.bank-select');
            
            let isDuplicate = false;
            selects.forEach(function(select) {
                if (select !== e.target && select.value === currentValue) {
                    isDuplicate = true;
                }
            });

            if (isDuplicate) {
                alert('ไม่สามารถเลือกบัญชีซ้ำได้');
                e.target.value = '';
            }
        }
    });
});