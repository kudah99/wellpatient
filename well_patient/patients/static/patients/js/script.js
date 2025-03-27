// Well PATIENT application JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    // Automatically add Bootstrap classes to Django form fields
    function bootstrapifyForms() {
        // Add form-control class to input fields
        const formControls = document.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], input[type="tel"], input[type="number"], input[type="date"], input[type="datetime-local"], textarea');
        formControls.forEach(function(input) {
            input.classList.add('form-control');
        });
        
        // Add form-select class to select fields
        const selects = document.querySelectorAll('select');
        selects.forEach(function(select) {
            select.classList.add('form-select');
        });
        
        // Add form-check-input class to checkboxes and radios
        const checkboxes = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
        checkboxes.forEach(function(checkbox) {
            checkbox.classList.add('form-check-input');
        });
    }
    
    bootstrapifyForms();

    // File Upload Handling for Import
    const fileUpload = document.getElementById('id_file');
    const fileLabel = document.querySelector('.file-label');
    const uploadArea = document.querySelector('.upload-area');

    if (fileUpload && fileLabel) {
        fileUpload.addEventListener('change', function() {
            if (fileUpload.files.length > 0) {
                fileLabel.textContent = fileUpload.files[0].name;
                if (uploadArea) {
                    uploadArea.classList.add('border-primary');
                }
            } else {
                fileLabel.textContent = 'Choose file';
                if (uploadArea) {
                    uploadArea.classList.remove('border-primary');
                }
            }
        });

        // Allow drag and drop file upload
        if (uploadArea) {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            ['dragenter', 'dragover'].forEach(eventName => {
                uploadArea.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                uploadArea.addEventListener(eventName, unhighlight, false);
            });

            function highlight() {
                uploadArea.classList.add('border-primary', 'bg-light');
            }

            function unhighlight() {
                uploadArea.classList.remove('border-primary', 'bg-light');
            }

            uploadArea.addEventListener('drop', handleDrop, false);

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;

                if (files.length > 0) {
                    fileUpload.files = files;
                    const event = new Event('change');
                    fileUpload.dispatchEvent(event);
                }
            }
        }
    }

    // Character counter for message textarea
    const messageTextarea = document.getElementById('id_message');
    const charCounter = document.getElementById('character-count');

    if (messageTextarea && charCounter) {
        updateCharCount();
        
        messageTextarea.addEventListener('input', updateCharCount);
        
        function updateCharCount() {
            const count = messageTextarea.value.length;
            charCounter.textContent = count + ' characters';
            
            if (count > 140 && count <= 160) {
                charCounter.className = 'form-text text-warning';
            } else if (count > 160) {
                charCounter.className = 'form-text text-danger';
            } else {
                charCounter.className = 'form-text';
            }
        }
    }

    // Auto-dismissing alerts
    const autoAlerts = document.querySelectorAll('.alert-auto-dismiss');
    autoAlerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });
    
    // Date range picker initialization for filters if available
    if (typeof flatpickr !== 'undefined') {
        const dateRangePickers = document.querySelectorAll('.date-range-picker');
        dateRangePickers.forEach(function(picker) {
            flatpickr(picker, {
                mode: "range",
                dateFormat: "Y-m-d"
            });
        });
    }
});
