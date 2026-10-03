document.addEventListener('DOMContentLoaded', () => {
    const trigger = document.getElementById('dashboard-report-trigger');
    const popup = document.getElementById('dashboard-report-popup');
    const closeButton = document.getElementById('dashboard-report-close');
    const closeAction = document.getElementById('dashboard-report-close-action');
    const printButton = document.getElementById('dashboard-report-print');
    const content = document.getElementById('dashboard-report-content');
    const generatedAt = document.getElementById('dashboard-report-generated');

    if (!trigger || !popup || !content) return;

    const escapeHtml = value => String(value ?? 'Not specified')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');

    const value = (object, key) => Number(object?.[key] || 0).toLocaleString();

    const buildMetric = (label, metric, note = '') => `
        <div class="dashboard-report__metric">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(metric)}</strong>
            ${note ? `<small>${escapeHtml(note)}</small>` : ''}
        </div>`;

    const buildReport = report => {
        const summary = report.summary || {};
        const occupations = report.occupations || [];
        const diagnoses = report.diagnoses || [];
        const corneal = report.corneal || [];
        const dominance = report.dominance || {};
        const systemic = report.systemic || [];
        const percentage = (object, key) => `${Number(object?.[key] || 0).toFixed(1)}%`;
        const share = (part, total) => {
            const denominator = Number(total || 0);
            return denominator > 0 ? `${(Number(part || 0) / denominator * 100).toFixed(1)}%` : '0.0%';
        };
        const concordance = Number(summary.diagnosed_inferences || 0) > 0
            ? `${(Number(summary.concordant_inferences || 0) / Number(summary.diagnosed_inferences) * 100).toFixed(1)}%`
            : 'N/A';

        const occupationRows = occupations.length
            ? occupations.map(item => `<tr><td>${escapeHtml(item.occupation)}</td><td>${value(item, 'patients')}</td><td>${value(item, 'myopic_patients')}</td><td>${value(item, 'hyperopic_patients')}</td><td>${value(item, 'emmetropic_patients')}</td><td>${value(item, 'astigmatism_patients')}</td></tr>`).join('')
            : '<tr><td colspan="6">No occupation data found.</td></tr>';
        const diagnosisRows = diagnoses.length
            ? diagnoses.map(item => `<li><span>${escapeHtml(item.diagnosis)}</span><strong>${value(item, 'diagnosis_count')}</strong></li>`).join('')
            : '<li><span>No diagnoses found.</span><strong>0</strong></li>';
        const cornealRows = corneal.length
            ? corneal.map(item => `<tr><td>${escapeHtml(item.age_group)}</td><td>${escapeHtml(item.average_pachymetry)}</td><td>${escapeHtml(item.average_k1)}</td><td>${escapeHtml(item.average_k2)}</td><td>${escapeHtml(item.average_axis)}</td></tr>`).join('')
            : '<tr><td colspan="5">No corneal measurements found.</td></tr>';
        const systemicRows = systemic.length
            ? systemic.map(item => `<li><span>${escapeHtml(item.factor)}</span><strong>${value(item, 'patient_count')}</strong></li>`).join('')
            : '<li><span>No systemic history factors found.</span><strong>0</strong></li>';

        content.innerHTML = `
            <section class="dashboard-report__section">
                <h3>Demographics &amp; patient base</h3>
                <div class="dashboard-report__metrics">
                    ${buildMetric('Total patients', value(summary, 'total_patients'))}
                    ${buildMetric('Average age', `${summary.average_age ?? 0} years`)}
                    ${buildMetric('Male', value(summary, 'male_patients'))}
                    ${buildMetric('Female', value(summary, 'female_patients'))}
                </div>
                <div class="dashboard-report__insight-grid">
                    <div><h4>Age distribution</h4><ul><li><span>Pediatric (&lt;18)</span><strong>${value(summary, 'pediatric_patients')}</strong></li><li><span>Adult (18-64)</span><strong>${value(summary, 'adult_patients')}</strong></li><li><span>Senior (65+)</span><strong>${value(summary, 'senior_patients')}</strong></li></ul></div>
                    <div><h4>Gender breakdown</h4><p>Male <strong>${share(summary.male_patients, summary.total_patients)}</strong> &middot; Female <strong>${share(summary.female_patients, summary.total_patients)}</strong></p></div>
                </div>
                <div class="dashboard-report__table-wrap"><table><caption>Top 10 occupations and refractive diagnoses</caption><thead><tr><th>Occupation</th><th>Patients</th><th>Myopic</th><th>Hyperopic</th><th>Emmetropic</th><th>Astigmatism</th></tr></thead><tbody>${occupationRows}</tbody></table></div>
            </section>
            <section class="dashboard-report__section">
                <h3>AI inference &amp; predictive analytics</h3>
                <div class="dashboard-report__metrics">
                    ${buildMetric('Linked inferences', value(summary, 'linked_inferences'))}
                    ${buildMetric(
                        'Unlinked walk-ins', 
                        value(summary, 'unlinked_inferences'), 
                        `Linked ${share(summary.linked_inferences, summary.total_inferences)} · Unlinked ${share(summary.unlinked_inferences, summary.total_inferences)}`
                    )}                    
                    ${buildMetric('Diagnosed inferences', value(summary, 'diagnosed_inferences'))}
                    ${buildMetric('AI concordance', concordance)}
                </div>
                <div class="dashboard-report__insight-grid">
                    <div><h4>Condition prevalence</h4><ul><li><span>Myopia</span><strong>${percentage(summary, 'myopia_percentage')}</strong></li><li><span>Hyperopia</span><strong>${percentage(summary, 'hyperopia_percentage')}</strong></li><li><span>Normal / Emmetropia</span><strong>${percentage(summary, 'emmetropia_percentage')}</strong></li></ul></div>
                    <div><h4>Model confidence averages</h4><ul><li><span>Myopia probability</span><strong>${percentage(summary, 'average_myopia_probability')}</strong></li><li><span>Hyperopia probability</span><strong>${percentage(summary, 'average_hyperopia_probability')}</strong></li><li><span>Normal probability</span><strong>${percentage(summary, 'average_emmetropia_probability')}</strong></li></ul></div>
                </div>
                <p class="dashboard-report__distribution">Concordant predictions: <strong>${value(summary, 'concordant_inferences')}</strong> of <strong>${value(summary, 'diagnosed_inferences')}</strong> inference results with clinician diagnoses.</p>
            </section>
            <section class="dashboard-report__section">
                <h3>Clinical &amp; refractive trends</h3>
                <div class="dashboard-report__insight-grid">
                    <div><h4>Top clinical diagnoses</h4><ul>${diagnosisRows}</ul></div>
                    <div><h4>Systemic risk factors</h4><ul>${systemicRows}</ul></div>
                </div>
                <div class="dashboard-report__table-wrap"><table><caption>Corneal health averages by age group</caption><thead><tr><th>Age group</th><th>Pachymetry</th><th>K1</th><th>K2</th><th>Axis</th></tr></thead><tbody>${cornealRows}</tbody></table></div>
                <div class="dashboard-report__dominance"><h4>Eye dominance traits</h4><p>Master eye: OD <strong>${share(dominance.master_od, Number(dominance.master_od || 0) + Number(dominance.master_os || 0))}</strong> &middot; OS <strong>${share(dominance.master_os, Number(dominance.master_od || 0) + Number(dominance.master_os || 0))}</strong></p><p>Rifle eye: OD <strong>${share(dominance.rifle_od, Number(dominance.rifle_od || 0) + Number(dominance.rifle_os || 0))}</strong> &middot; OS <strong>${share(dominance.rifle_os, Number(dominance.rifle_od || 0) + Number(dominance.rifle_os || 0))}</strong></p></div>
            </section>`;
    };

    const closeReport = () => {
        popup.classList.remove('active');
        popup.setAttribute('aria-hidden', 'true');
        trigger.focus();
    };

    trigger.addEventListener('click', async () => {
        popup.classList.add('active');
        popup.setAttribute('aria-hidden', 'false');
        content.innerHTML = '<p class="dashboard-report__loading">Loading report details...</p>';
        closeButton.focus();

        try {
            const response = await fetch('/api/dashboard-report');
            if (!response.ok) throw new Error('Report request failed');
            const report = await response.json();
            buildReport(report);
            generatedAt.textContent = `Generated ${report.generated_at}`;
        } catch (error) {
            content.innerHTML = '<p class="dashboard-report__error">The detailed report could not be loaded. Please try again.</p>';
            console.error('Dashboard report error:', error);
        }
    });

    closeButton.addEventListener('click', closeReport);
    closeAction.addEventListener('click', closeReport);
    printButton.addEventListener('click', () => window.print());
    popup.addEventListener('click', event => {
        if (event.target === popup) closeReport();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && popup.classList.contains('active')) closeReport();
    });
});
