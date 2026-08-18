document.addEventListener("DOMContentLoaded", () => {
    const classNames = ["myopia", "hyperopia", "emmetropia"];

    classNames.forEach(cls => {
        const probElement = document.getElementById(`${cls}-probability`);
        const barBgElement = document.querySelector(`.container-${cls}-bar-bg`) || document.querySelector(`.${cls} .container-${cls}-bar-bg`);

        if (probElement && barBgElement) {
            // parseFloat automatically strips the '%' character (e.g., "90.5%" -> 90.5)
            let probValue = parseFloat(probElement.textContent.trim()) || 0;

            // Handle decimal values (e.g. 0.90 -> 90)
            if (probValue <= 1.0) {
                probValue *= 100;
            }

            const paddingRight = Math.max(0, 100 - probValue);
            barBgElement.style.paddingRight = `${paddingRight}%`;
        }
    });
});