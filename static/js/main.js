        let currentDocument = null;
        let lastAction = null;
        let allDirectories = [];
        let globalDirectories = [];
        let directoryStructure = {};
        window.appCategories = [];

        // Dateien aus Scan-Verzeichnis laden
        async function loadFiles() {
            try {
                const response = await fetch('/api/scan-files');
                const data = await response.json();

                const container = document.getElementById('file-list-container');

                if (data.files && data.files.length > 0) {
                    container.innerHTML = data.files.map(file => `
                        <div class="file-item" onclick="selectFile('${file.path}', '${file.name}')">
                            <div class="file-name">
                                ${file.name}
                                ${file.preloaded ? '<span class="preloaded-indicator">⚡ Geladen</span>' : ''}
                                ${file.suggested_category ? `<span class="suggested-category-badge">${file.suggested_category}</span>` : ''}
                            </div>
                            <div class="file-meta">
                                ${(file.size / 1024).toFixed(1)} KB<br>
                                ${new Date(file.modified).toLocaleString('de-DE')}
                            </div>
                        </div>
                    `).join('');

                    // System-Status aktualisieren
                    updateSystemStatus(data.system_stats, data.preload_status, data.cached_count, data.files.length);
                } else {
                    container.innerHTML = '<div class="loading">Keine PDF-Dateien gefunden</div>';
                }
            } catch (error) {
                console.error('Error loading files:', error);
                document.getElementById('file-list-container').innerHTML =
                    '<div class="loading">Fehler beim Laden der Dateien</div>';
            }
        }

        // Datei auswählen und verarbeiten
        async function selectFile(path, name) {
            // UI-Update: Aktive Datei markieren
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.closest('.file-item').classList.add('active');

            // Loading-Anzeige
            document.getElementById('unified-content').innerHTML =
                '<div class="loading">Verarbeite Dokument...</div>';

            try {
                const response = await fetch('/api/process-document', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ path: path })
                });


                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('API Error:', errorText);
                    showStatus(`API Fehler (${response.status}): ${errorText}`, 'error');
                    return;
                }

                const data = await response.json();

                if (data && data.preview) {
                    currentDocument = data;
                    // Update document header
                    updateDocumentHeader(data, name);
                    displayNewWorkflow(data, name);
                } else {
                    console.error('Invalid response data:', data);
                    showStatus('Ungültige API-Antwort: Fehlende Daten', 'error');
                }
            } catch (error) {
                console.error('Error processing document:', error);
                showStatus(`Fehler bei der Dokumentenverarbeitung: ${error.message}`, 'error');
            }
        }

        // New 3-column workflow display
        function displayNewWorkflow(data, filename) {
            try {

                if (!data || !data.preview) {
                    console.error('Missing required data fields:', data);
                    showStatus('Fehler: Unvollständige Dokumentdaten', 'error');
                    return;
                }

                if (!window.appCategories || window.appCategories.length === 0) {
                    console.error('Categories not loaded yet');
                    showStatus('Fehler: Kategorien nicht geladen', 'error');
                    return;
                }

                const suggestedCategory = data.suggested_category || window.appCategories[0];

                // Create Unified Workflow Content
                const unifiedContent = createUnifiedContent(data, filename);
                document.getElementById('unified-content').innerHTML = unifiedContent;

                // Update found details section
                const foundDetailsContent = createFoundDetailsContent(data);
                if (foundDetailsContent) {
                    document.getElementById('found-details-content').innerHTML = foundDetailsContent;
                    document.getElementById('found-details-section').style.display = 'block';
                } else {
                    document.getElementById('found-details-section').style.display = 'none';
                }

                // Set AI indicator based on confidence
                setAIIndicator(data);

                // Setup event listeners
                setupNewWorkflowEvents();

                // Load initial subcategories for unified workflow
                setTimeout(() => {
                    updateSubcategories();
                    loadDirectoryStructureManual();
                }, 100);

            } catch (error) {
                console.error('Error in displayNewWorkflow:', error);
                showStatus(`Fehler beim Anzeigen des Dokuments: ${error.message}`, 'error');
            }
        }

        function createUnifiedContent(data, filename) {
            return `
                <div class="unified-workflow">
                    <!-- Category and Path Selection -->
                    <div class="workflow-section">
                        <h4>📂 Kategorie und Pfad auswählen</h4>
                        <div class="category-hierarchy">
                            <div class="category-item">
                                <label>Kategorie ${data.suggested_category ? '🤖' : ''}</label>
                                <select id="category-select" class="category-select" onchange="updateSubcategories()">
                                    ${window.appCategories.map(cat =>
                                        `<option value="${cat}" ${cat === data.suggested_category ? 'selected' : ''}>${cat}</option>`
                                    ).join('')}
                                </select>
                            </div>

                            <div class="category-item">
                                <label>Unterkategorie ${data.suggested_subdirectory ? '🤖' : ''}</label>
                                <select id="subcategory-select" class="subcategory-select" onchange="updateSubSubcategories()">
                                    <option value="">Keine Unterkategorie</option>
                                    ${data.suggested_subdirectory ? `<option value="${data.suggested_subdirectory}" selected>${data.suggested_subdirectory}</option>` : ''}
                                </select>
                            </div>

                            <div class="category-item">
                                <label>Unter-Unterkategorie <span class="optional-hint">(optional)</span></label>
                                <select id="subsubcategory-select" class="subcategory-select" onchange="updatePathDisplay()">
                                    <option value="">Keine Unter-Unterkategorie</option>
                                </select>
                            </div>

                            <div class="category-item">
                                <label>Zielpfad <span class="optional-hint">(kann angepasst werden)</span></label>
                                <input type="text" id="manual-path-input" class="path-input"
                                       value="${data.suggested_path || ''}" placeholder="Automatisch generierter Pfad">
                            </div>
                        </div>
                    </div>

                    <!-- Filename Selection -->
                    <div class="workflow-section">
                        <h4>📝 Dateiname</h4>
                        <div class="filename-options-simple">
                            <div class="filename-option-simple">
                                <input type="radio" id="unified-original" name="unified-filename" value="original" checked>
                                <label for="unified-original">📄 Original: ${filename}</label>
                            </div>
                            ${data.filename_suggestion ? `
                            <div class="filename-option-simple">
                                <input type="radio" id="unified-smart" name="unified-filename" value="smart">
                                <label for="unified-smart">✨ Intelligent: ${data.filename_suggestion.suggested_filename}</label>
                            </div>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Action Button -->
                    <div class="workflow-actions">
                        <button class="btn btn-primary" onclick="executeUnifiedWorkflow()">
                            📁 Dokument verschieben
                        </button>
                    </div>
                </div>
            `;
        }

        function createFoundDetailsContent(data) {
            if (!data.filename_suggestion) return '';

            let html = '<div class="details-grid">';

            // Extracted dates
            if (data.filename_suggestion.extracted_dates && data.filename_suggestion.extracted_dates.length > 0) {
                const dates = data.filename_suggestion.extracted_dates.slice(0, 3);
                html += `
                    <div class="detail-card">
                        <div class="detail-label">Datum</div>
                        <div class="detail-value clickable-value" onclick="useDate('${dates[0]}')">${dates[0]}</div>
                    </div>`;
            }

            // Extracted title
            if (data.filename_suggestion.extracted_title) {
                const title = data.filename_suggestion.extracted_title.length > 30
                    ? data.filename_suggestion.extracted_title.substring(0, 30) + '...'
                    : data.filename_suggestion.extracted_title;
                html += `
                    <div class="detail-card">
                        <div class="detail-label">Titel</div>
                        <div class="detail-value clickable-value" onclick="useTitle('${data.filename_suggestion.extracted_title}')">${title}</div>
                    </div>`;
            }

            // Subject keywords (first one only)
            if (data.filename_suggestion.subject_keywords && data.filename_suggestion.subject_keywords.length > 0) {
                html += `
                    <div class="detail-card">
                        <div class="detail-label">Kategorie</div>
                        <div class="detail-value clickable-value" onclick="useKeyword('${data.filename_suggestion.subject_keywords[0]}')">${data.filename_suggestion.subject_keywords[0]}</div>
                    </div>`;
            }

            // Letterhead companies (first one only)
            if (data.filename_suggestion.letterhead_companies && data.filename_suggestion.letterhead_companies.length > 0) {
                html += `
                    <div class="detail-card">
                        <div class="detail-label">Firma</div>
                        <div class="detail-value clickable-value" onclick="useCompany('${data.filename_suggestion.letterhead_companies[0]}')">${data.filename_suggestion.letterhead_companies[0]}</div>
                    </div>`;
            }

            html += '</div>';
            return html;
        }

        function createIntelligentContent(data, filename) {
            // This function is now deprecated but kept for compatibility
            return createUnifiedContent(data, filename);
        }

        function createManualContent(data, filename, suggestedCategory) {
            // This function is now deprecated, use createUnifiedContent instead
            return createUnifiedContent(data, filename);
        }

        // Move-Operation ausführen
        async function executeMove() {
            if (!currentDocument) return;

            // Use the suggested path input field as primary source
            const suggestedPathInput = document.getElementById('suggested-path-input');
            const pathDisplay = document.querySelector('.suggested-path-display');
            const finalPath = suggestedPathInput ? suggestedPathInput.value :
                             (pathDisplay ? pathDisplay.textContent : currentDocument.suggested_path);

            try {
                const response = await fetch('/api/move-document', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        source_path: currentDocument.original_path,
                        target_path: finalPath
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    // Speichere letzte Aktion für Undo
                    lastAction = {
                        type: 'move',
                        source_path: finalPath,
                        target_path: currentDocument.original_path,
                        timestamp: new Date().toISOString()
                    };
                    document.getElementById('undo-btn').disabled = false;

                    showStatus(`✅ Datei erfolgreich verschoben nach: ${finalPath}`, 'success');
                    // Dateiliste neu laden
                    setTimeout(() => {
                        loadFiles();
                        document.getElementById('unified-content').innerHTML =
                            '<div class="loading">Wähle eine neue Datei aus der Liste</div>';
                        document.getElementById('found-details-section').style.display = 'none';
                    }, 2000);
                } else {
                    showStatus(`❌ Fehler: ${data.error}`, 'error');
                }
            } catch (error) {
                console.error('Error moving document:', error);
                showStatus('❌ Fehler beim Verschieben der Datei', 'error');
            }
        }

        // Zufälliges Dokument auswählen
        async function selectRandomDocument() {
            try {
                const response = await fetch('/api/random-document');
                const randomDoc = await response.json();

                if (response.ok) {
                    // Vorhandene selectFile Funktion aufrufen
                    selectFile(randomDoc.path, randomDoc.name);

                    // Visuelles Feedback
                    const fileItems = document.querySelectorAll('.file-item');
                    fileItems.forEach(item => {
                        if (item.querySelector('.file-name').textContent.includes(randomDoc.name)) {
                            item.classList.add('active');
                            item.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        } else {
                            item.classList.remove('active');
                        }
                    });
                } else {
                    showStatus(`❌ Fehler: ${randomDoc.error}`, 'error');
                }
            } catch (error) {
                console.error('Error selecting random document:', error);
                showStatus('❌ Fehler beim Auswählen eines zufälligen Dokuments', 'error');
            }
        }

        // Status-Nachricht anzeigen
        function showStatus(message, type) {
            const statusContainer = document.getElementById('status-container');
            statusContainer.innerHTML = `
                <div class="status-message status-${type}">
                    ${message}
                </div>
            `;

            // Nach 5 Sekunden automatisch ausblenden
            setTimeout(() => {
                statusContainer.innerHTML = '';
            }, 5000);
        }

        function updateSystemStatus(systemStats, preloadStatus, cachedCount, totalFiles) {
            // Element existiert nicht mehr, nur Footer aktualisieren
            updateSystemMetricsFooter(systemStats, preloadStatus, cachedCount, totalFiles);
        }

        // Intelligentes Refresh-System
        let refreshInterval;

        function startSmartRefresh() {
            // Kontinuierliches Refresh für Systemmetriken
            if (refreshInterval) clearInterval(refreshInterval);

            refreshInterval = setInterval(async () => {
                try {
                    const response = await fetch('/api/system-status');
                    const data = await response.json();

                    // Aktualisiere Footer-Metriken
                    updateSystemMetricsFooter(data.system_stats, data.preload_status, data.cached_count, 0);

                } catch (error) {
                    console.error('Error updating system metrics:', error);
                }
            }, 5000); // Alle 5 Sekunden

            // Initial Update
            updateSystemMetrics();
        }

        async function updateSystemMetrics() {
            try {
                const response = await fetch('/api/system-status');
                const data = await response.json();
                updateSystemMetricsFooter(data.system_stats, data.preload_status, data.cached_count, 0);
            } catch (error) {
                console.error('Error loading initial system metrics:', error);
            }
        }

        // AI Indicator setzen basierend auf Confidence und Fallback-Status
        function setAIIndicator(data) {
            const indicator = document.getElementById('ai-indicator');
            if (!indicator) return;

            // Bestimme ob AI oder Fallback verwendet wurde
            const isAIPowered = data.confidence === 'high' && !data.fallback_used;

            if (isAIPowered) {
                indicator.className = 'ai-indicator ai-powered';
                indicator.textContent = '🤖 KI-Vorschlag';
                indicator.title = 'Dieser Pfad wurde von der KI vorgeschlagen';
            } else {
                indicator.className = 'ai-indicator fallback';
                indicator.textContent = '🔄 Fallback';
                indicator.title = 'Dieser Pfad wurde vom Fallback-System vorgeschlagen (KI nicht verfügbar)';
            }
        }

        // Kategorien vom Backend laden
        async function loadCategories() {
            try {
                const response = await fetch('/api/directory-structure');
                const data = await response.json();

                // Extract directory names as categories from structure
                if (data.structure && typeof data.structure === 'object') {
                    window.appCategories = Object.keys(data.structure).sort();
                } else {
                    // Fallback if structure is not available
                    window.appCategories = Object.keys(data).filter(key => key !== 'base_path').sort();
                }
            } catch (error) {
                console.error('Error loading categories:', error);
                // Fallback Kategorien - aus Documents-Struktur
                window.appCategories = [
                    '0001_scanbot', '10_arbeit', '11 finanzen', '12 schriftverkehr',
                    '13 telefon internet', '14 telekommunikation', '15 versicherung',
                    '16 wohnen', '17 sonstiges', '18 gesundheit', '19 fahrzeuge',
                    '1_halle', '20 steuern', '21_gifs', '2 persönliche dokumente',
                    '3a Gesundheit', '4 Verträge', '5 Finanzen', '6 Politik',
                    '7 Arbeit', '8 wohnen', '9 Fahrzeuge', 'arbeit', 'Sonstiges'
                ];
            }
        }

        async function undoLastAction() {
            if (!lastAction) return;

            try {
                const response = await fetch('/api/move-document', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        source_path: lastAction.source_path,
                        target_path: lastAction.target_path
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showStatus(`↶ Aktion rückgängig gemacht: Datei zurück nach ${lastAction.target_path}`, 'success');
                    lastAction = null;
                    document.getElementById('undo-btn').disabled = true;

                    // Dateiliste neu laden
                    setTimeout(() => {
                        loadFiles();
                        document.getElementById('unified-content').innerHTML =
                            '<div class="loading">Wähle eine neue Datei aus der Liste</div>';
                        document.getElementById('found-details-section').style.display = 'none';
                    }, 2000);
                } else {
                    showStatus(`❌ Fehler beim Rückgängigmachen: ${data.error}`, 'error');
                }
            } catch (error) {
                console.error('Error undoing action:', error);
                showStatus('❌ Fehler beim Rückgängigmachen der Aktion', 'error');
            }
        }

        // Initial laden und Smart Refresh starten
        async function initializeApp() {
            try {
                await loadCategories();
                await loadFiles();
                startSmartRefresh();
            } catch (error) {
                console.error('Initialization error:', error);
                // Fallback: Versuche trotzdem zu laden
                window.appCategories = ['Sonstiges'];
                loadFiles();
                startSmartRefresh();
            }
        }

        // DOM ready checker
        function updateSystemMetricsFooter(systemStats, preloadStatus, cachedCount, totalFiles) {
            document.getElementById('cpu-usage').textContent = `${systemStats.cpu_percent || 0}%`;
            document.getElementById('memory-usage').textContent = `${systemStats.memory_percent || 0}%`;
            document.getElementById('disk-usage').textContent = `${systemStats.disk_usage || 0}%`;
            document.getElementById('cached-files').textContent = cachedCount || 0;

            // LM Studio status indicator
            const lmStudioStatus = document.getElementById('lm-studio-status');
            if (preloadStatus.is_running) {
                lmStudioStatus.textContent = '🟢';
                lmStudioStatus.title = 'LM Studio aktiv';
            } else {
                lmStudioStatus.textContent = '⚪';
                lmStudioStatus.title = 'LM Studio bereit';
            }
        }

        // New Workflow Functions
        function setupNewWorkflowEvents() {
            // Setup initial path display
            updatePathDisplay();
        }

        function useDate(date) {
            if (currentDocument && currentDocument.filename_suggestion) {
                currentDocument.filename_suggestion.selected_date = date;

                // Update filename display
                const cleanName = currentDocument.filename_suggestion.original_filename.replace(/^\d{4}-\d{2}-\d{2}_?/, '');
                const newFilename = `${date}_${cleanName}`;

                currentDocument.filename_suggestion.suggested_filename = newFilename;
                showStatus(`📅 Datum ${date} für Dateiname verwendet`, 'success');
            }
        }

        function useTitle(title) {
            if (currentDocument && currentDocument.filename_suggestion) {
                const date = currentDocument.filename_suggestion.selected_date || new Date().toISOString().split('T')[0];
                const newFilename = `${date}_${title}.pdf`;

                currentDocument.filename_suggestion.suggested_filename = newFilename;
                showStatus(`📄 Titel "${title}" für Dateiname verwendet`, 'success');
            }
        }

        function updateDocumentHeader(data, filename) {
            const header = document.getElementById('document-header');
            const title = document.getElementById('document-title');
            const path = document.getElementById('document-path');
            const previewImg = document.getElementById('document-preview-img');

            if (data && filename) {
                title.textContent = filename;
                path.textContent = data.original_path || '-';
                previewImg.src = data.preview || '';
                header.style.display = 'flex';
            } else {
                title.textContent = 'Kein Dokument ausgewählt';
                path.textContent = '-';
                previewImg.src = '';
                header.style.display = 'none';
            }
        }

        async function loadSubcategoriesForCategory(category) {
            try {
                const response = await fetch('/api/directory-structure');
                const data = await response.json();

                if (data.structure && data.structure[category] && data.structure[category].children) {
                    return Object.keys(data.structure[category].children);
                }
                return [];
            } catch (error) {
                console.error('Error loading subcategories:', error);
                return [];
            }
        }

        async function updateSubcategories() {
            const categorySelect = document.getElementById('category-select');
            const subcategorySelect = document.getElementById('subcategory-select');
            const subsubcategorySelect = document.getElementById('subsubcategory-select');

            if (!categorySelect || !subcategorySelect) return;

            const selectedCategory = categorySelect.value;
            const subcategories = await loadSubcategoriesForCategory(selectedCategory);

            // Clear and populate subcategory dropdown
            subcategorySelect.innerHTML = '<option value="">Keine Unterkategorie</option>';
            subcategories.forEach(subcat => {
                const option = document.createElement('option');
                option.value = subcat;
                option.textContent = subcat;
                subcategorySelect.appendChild(option);
            });

            // Clear sub-subcategory dropdown when category changes
            if (subsubcategorySelect) {
                subsubcategorySelect.innerHTML = '<option value="">Keine Unter-Unterkategorie</option>';
            }

            updatePathDisplay();
        }

        async function updateSubSubcategories() {
            const categorySelect = document.getElementById('category-select');
            const subcategorySelect = document.getElementById('subcategory-select');
            const subsubcategorySelect = document.getElementById('subsubcategory-select');

            if (!categorySelect || !subcategorySelect || !subsubcategorySelect) return;

            const selectedCategory = categorySelect.value;
            const selectedSubcategory = subcategorySelect.value;

            // Clear sub-subcategory dropdown
            subsubcategorySelect.innerHTML = '<option value="">Keine Unter-Unterkategorie</option>';

            if (!selectedSubcategory) {
                updatePathDisplay();
                return;
            }

            try {
                const response = await fetch('/api/directory-structure');
                const data = await response.json();

                // Navigate to the specific subcategory
                const categoryPath = data.structure?.[selectedCategory];
                const subcategoryPath = categoryPath?.children?.[selectedSubcategory];

                if (subcategoryPath?.children && Object.keys(subcategoryPath.children).length > 0) {
                    Object.keys(subcategoryPath.children).forEach(subsubcat => {
                        const option = document.createElement('option');
                        option.value = subsubcat;
                        option.textContent = subsubcat;
                        subsubcategorySelect.appendChild(option);
                    });
                }

                updatePathDisplay();
            } catch (error) {
                console.error('Error loading sub-subcategories:', error);
                updatePathDisplay();
            }
        }

        function updatePathDisplay() {
            const categorySelect = document.getElementById('category-select');
            const subcategorySelect = document.getElementById('subcategory-select');
            const subsubcategorySelect = document.getElementById('subsubcategory-select');
            const pathInput = document.getElementById('manual-path-input');

            if (!categorySelect || !subcategorySelect || !pathInput || !currentDocument) return;

            const selectedCategory = categorySelect.value;
            const selectedSubcategory = subcategorySelect.value;
            const selectedSubsubcategory = subsubcategorySelect ? subsubcategorySelect.value : '';

            // Build path based on current selection
            const filename = getSelectedFilename();
            const sortedDir = currentDocument.suggested_path.split('/').slice(0, -2).join('/');

            let targetPath = `${sortedDir}/${selectedCategory}`;
            if (selectedSubcategory) {
                targetPath += `/${selectedSubcategory}`;
                if (selectedSubsubcategory) {
                    targetPath += `/${selectedSubsubcategory}`;
                }
            }
            targetPath += `/${filename}`;

            pathInput.value = targetPath;
        }

        function selectSubdirectory(subdirectory) {
            const subcategorySelect = document.getElementById('subcategory-select');
            if (subcategorySelect) {
                subcategorySelect.value = subdirectory;
                showStatus(`🤖 KI-Unterkategorie "${subdirectory}" ausgewählt`, 'success');
            }
        }

        function useKeyword(keyword) {
            // Use a keyword as part of the filename
            if (currentDocument && currentDocument.filename_suggestion) {
                const date = currentDocument.filename_suggestion.selected_date || new Date().toISOString().split('T')[0];
                const newFilename = `${date}_${keyword}.pdf`;

                // Update manual smart option if it exists
                const smartLabel = document.querySelector('label[for="unified-smart"]');
                if (smartLabel) {
                    smartLabel.innerHTML = `✨ Intelligent: ${newFilename}`;
                }

                currentDocument.filename_suggestion.suggested_filename = newFilename;
                showStatus(`🏷️ Kategorie "${keyword}" für Dateiname verwendet`, 'success');
            }
        }

        function useCompany(company) {
            // Use a company name as part of the filename
            if (currentDocument && currentDocument.filename_suggestion) {
                const date = currentDocument.filename_suggestion.selected_date || new Date().toISOString().split('T')[0];
                const newFilename = `${date}_${company}.pdf`;

                // Update manual smart option if it exists
                const smartLabel = document.querySelector('label[for="unified-smart"]');
                if (smartLabel) {
                    smartLabel.innerHTML = `✨ Intelligent: ${newFilename}`;
                }

                currentDocument.filename_suggestion.suggested_filename = newFilename;
                showStatus(`🏢 Unternehmen "${company}" für Dateiname verwendet`, 'success');
            }
        }

        function executeUnifiedWorkflow() {
            if (!currentDocument) {
                showStatus('Kein Dokument ausgewählt', 'error');
                return;
            }

            const categorySelect = document.getElementById('category-select');
            const subcategorySelect = document.getElementById('subcategory-select');
            const filenameRadios = document.querySelectorAll('input[name="unified-filename"]');

            const sourcePath = currentDocument.original_path;

            let filename;
            const selectedRadio = Array.from(filenameRadios).find(radio => radio.checked);

            if (selectedRadio && selectedRadio.value === 'smart' && currentDocument.filename_suggestion) {
                filename = currentDocument.filename_suggestion.suggested_filename;
            } else {
                filename = currentDocument.original_path.split('/').pop();
            }

            const category = categorySelect ? categorySelect.value : '';
            const subcategory = subcategorySelect ? subcategorySelect.value : '';

            const sortedDir = currentDocument.suggested_path.split('/').slice(0, -2).join('/');
            const targetPath = subcategory ?
                `${sortedDir}/${category}/${subcategory}/${filename}` :
                `${sortedDir}/${category}/${filename}`;

            executeMove(sourcePath, targetPath, 'Unified Workflow');
        }

        function executeMove(sourcePath, targetPath, workflowType) {
            showStatus(`${workflowType}: Dokument wird verschoben...`, 'info');

            fetch('/api/move-document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source_path: sourcePath,
                    target_path: targetPath
                })
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showStatus(`✅ ${workflowType}: Erfolgreich nach ${result.target_path}`, 'success');

                    // Refresh and clear
                    setTimeout(() => {
                        loadFiles();
                        document.getElementById('unified-content').innerHTML =
                            '<div class="loading">Wählen Sie eine neue Datei aus der Liste</div>';
                        currentDocument = null;
                    }, 2000);
                } else {
                    showStatus(`❌ ${workflowType}: Fehler - ${result.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showStatus(`❌ ${workflowType}: Fehler beim Verschieben`, 'error');
            });
        }



        function getSelectedFilename() {
            const filenameRadios = document.querySelectorAll('input[name="unified-filename"]');
            const selectedRadio = Array.from(filenameRadios).find(radio => radio.checked);

            if (selectedRadio && selectedRadio.value === 'smart' && currentDocument.filename_suggestion) {
                return currentDocument.filename_suggestion.suggested_filename;
            } else {
                return currentDocument.original_path.split('/').pop();
            }
        }

        async function deleteDocument() {
            if (!currentDocument) {
                showStatus('Kein Dokument ausgewählt', 'error');
                return;
            }

            const filename = currentDocument.original_path.split('/').pop();

            if (!confirm(`Sind Sie sicher, dass Sie die Datei "${filename}" dauerhaft löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.`)) {
                return;
            }

            try {
                const response = await fetch('/api/delete-document', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file_path: currentDocument.original_path
                    })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showStatus(`🗑️ Datei "${filename}" wurde erfolgreich gelöscht`, 'success');

                    // Refresh file list and clear content
                    setTimeout(() => {
                        loadFiles();
                        document.getElementById('unified-content').innerHTML =
                            '<div class="loading">Wählen Sie eine neue Datei aus der Liste</div>';
                        updateDocumentHeader(null, null);
                        currentDocument = null;
                    }, 2000);
                } else {
                    showStatus(`❌ Fehler beim Löschen: ${result.error || 'Unbekannter Fehler'}`, 'error');
                }
            } catch (error) {
                console.error('Error deleting document:', error);
                showStatus('❌ Fehler beim Löschen der Datei', 'error');
            }
        }


        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeApp);
        } else {
            initializeApp();
        }