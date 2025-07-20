function escapeCSV(str) {
    if (typeof str !== 'string') {
        str = String(str);
    }
    // If the string contains quotes, commas, or newlines, wrap in quotes and escape internal quotes
    if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
        return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
}

function tableToCSV(table) {
    const headerRows = table.querySelectorAll('tr');
    const rows = table.querySelectorAll('tr.form-row');
    const csvRows = [];
    
    // Get headers
    const headers = Array.from(headerRows[0].querySelectorAll('th'))
        .map(header => header.textContent.trim())
        .filter(header => header !== 'Delete?')
        .map(escapeCSV);
    csvRows.push(headers.join('\t'));
    
    // Get data rows
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        if (row.classList.contains('row-form-errors') || row.classList.contains('empty-form')) {
            continue;
        }
        
        const rowData = [];
        const cells = row.querySelectorAll('td');
        cells.forEach(cell => {
            // Skip delete column
            if (cell.classList.contains('delete')) {
                return;
            }
            
            // Try to find an input first
            const input = cell.querySelector('input[type="text"], input[type="number"], input[type="checkbox"], select, textarea');
            if (input && !input.name.includes('-DELETE')) {
                let value;
                if (input.type === 'checkbox') {
                    value = input.checked ? 'true' : 'false';
                } else if (input.type === 'select-one') {
                    const selectedOption = input.options[input.selectedIndex];
                    const optionText = selectedOption ? selectedOption.text : '';
                    value = input.value ? `${input.value} (${optionText})` : '';
                } else {
                    value = input.value || '';
                    if (input.type === 'number') {
                        // Keep original number format
                        value = value.replace(',', '.');
                    }
                }
                rowData.push(escapeCSV(value));
            } else {
                // If no input found, get the text content (for readonly fields)
                const text = cell.textContent.trim();
                rowData.push(escapeCSV(text));
            }
        });
        
        const rowString = rowData.join('\t');
        if (rowData.length > 0 && rowString.trim() !== '') {
            csvRows.push(rowString);
        }
    }
    
    // Add BOM for Excel UTF-8 compatibility
    return '\ufeff' + csvRows.join('\r\n');
}

$(function() {
    $(".export-tabularinline").click(function () {
        const fieldset = $(this).closest('fieldset');
        if (!fieldset.length) {
            console.error('No fieldset found');
            return;
        }
        
        const table = fieldset.find('table')[0];
        if (!table) {
            console.error('No table found in fieldset');
            return;
        }
        
        const csv = tableToCSV(table);
        navigator.clipboard.writeText(csv).then(() => {
            const button = $(this);
            const copyText = button.find('.copy-text');
            const copiedText = button.find('.copied-text');
            
            copyText.addClass('hidden');
            copiedText.removeClass('hidden');
            
            setTimeout(() => {
                copiedText.addClass('hidden');
                copyText.removeClass('hidden');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    });

    function parseTabSeparatedData(text) {
        return text.split(/[\r\n]+/).map(line => line.split('\t'));
    }

    function findInputInCell(cell) {
        return cell.querySelector('input[type="text"], input[type="number"], input[type="checkbox"], select, textarea');
    }

    function getReadOnlyValues(row) {
        const values = [];
        row.querySelectorAll('td:not(.delete)').forEach((cell, index) => {
            const input = findInputInCell(cell);
            if (!input) {
                const text = cell.textContent.trim();
                if (text) values.push({index, value: text});
            }
        });
        return values;
    }

    function getFirstColumnValue(row) {
        const firstCell = row.querySelector('td:not(.delete)');
        if (!firstCell) return null;
        
        const input = findInputInCell(firstCell);
        if (input) {
            return input.value.trim();
        }
        return firstCell.textContent.trim();
    }

    function findMatchingRow(rows, readOnlyFields, importedData) {
        return rows.find(row => {
            const rowReadOnlyValues = getReadOnlyValues(row);
            
            // If we have readonly values, use them for matching
            if (rowReadOnlyValues.length > 0) {
                return rowReadOnlyValues.every(({index, value}) => 
                    importedData[index] && value === importedData[index].trim()
                );
            }
            
            // Fallback to matching by first column value
            const firstColValue = getFirstColumnValue(row);
            return firstColValue && firstColValue === importedData[0].trim();
        });
    }

    $(".import-tabularinline").click(async function () {
        try {
            const fieldset = $(this).closest('fieldset');
            if (!fieldset.length) {
                console.error('No fieldset found');
                return;
            }

            const table = fieldset.find('table')[0];
            if (!table) {
                console.error('No table found in fieldset');
                return;
            }

            const text = await navigator.clipboard.readText();
            const data = text.split(/[\r\n]+/)
                .map(line => line.trim())
                .filter(line => line !== '')
                .map(line => line.split('\t'));

            if (!data.length) {
                alert('No data to import');
                return;
            }

            // Skip header row from imported data
            const importData = data.slice(1);

            // Get editable rows from table
            const rows = Array.from(table.querySelectorAll('tr.form-row:not(.empty-form)'));

            // Import data row by row
            importData.forEach(rowData => {
                // Find matching row based on readonly fields
                const matchingRow = findMatchingRow(rows, getReadOnlyValues(rows[0]), rowData);
                if (!matchingRow) {
                    console.warn('No matching row found for:', rowData);
                    return;
                }

                // Update editable fields in matching row
                const cells = matchingRow.querySelectorAll('td:not(.delete)');
                cells.forEach((cell, cellIndex) => {
                    if (cellIndex >= rowData.length) {
                        console.warn("Row data doesn't match cell count:", rowData);
                        return;
                    }
                    
                    const input = findInputInCell(cell);
                    if (input && !input.readOnly && !input.disabled) {
                        const value = rowData[cellIndex].trim();
                        if (value !== '') {
                            if (input.type === 'checkbox') {
                                input.checked = value.toLowerCase() === 'true';
                                $(input).trigger('change');
                            } else if (input.type === 'select-one') {
                                // Check if the value is in the format "value (text)"
                                const match = value.match(/^(.*?)\s*\((.*?)\)$/);
                                if (match) {
                                    const optionValue = match[1].trim();
                                    const optionText = match[2].trim();
                                    
                                    // Check if option exists
                                    let optionExists = false;
                                    for (let i = 0; i < input.options.length; i++) {
                                        if (input.options[i].value === optionValue) {
                                            optionExists = true;
                                            break;
                                        }
                                    }
                                    
                                    // Create option if it doesn't exist
                                    if (!optionExists && optionValue && optionText) {
                                        const newOption = document.createElement('option');
                                        newOption.value = optionValue;
                                        newOption.text = optionText;
                                        input.add(newOption);
                                    }
                                    
                                    // Set the value
                                    $(input).val(optionValue).trigger('change');
                                } else {
                                    // If not in the expected format, try to set the value directly
                                    $(input).val(value).trigger('change');
                                }
                            } else {
                                $(input).val(value).trigger('change');
                            }
                        } else {
                            console.warn("Empty value for input:", input);
                        }
                    } else {
                        console.warn('No editable input found for cell:', cell);
                    }
                });
            });

            const button = $(this);
            const importText = button.find('.import-text');
            const importedText = button.find('.imported-text');
            
            importText.addClass('hidden');
            importedText.removeClass('hidden');
            
            setTimeout(() => {
                importedText.addClass('hidden');
                importText.removeClass('hidden');
            }, 2000);
            
        } catch (err) {
            console.error('Failed to import:', err);
        }
    });
});
