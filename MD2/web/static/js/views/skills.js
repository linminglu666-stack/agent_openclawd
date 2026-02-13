
export default {
    render() {
        return `
            <div class="view-skills">
                <h1>Capabilities (Skills)</h1>
                <div id="skills-container" class="cards-grid">
                    Loading...
                </div>
            </div>
        `;
    },

    async mount(el) {
        const loadSkills = async () => {
            const res = await window.api.get('/skills');
            const container = el.querySelector('#skills-container');
            if (!container) return;
            container.innerHTML = '';

            if (!res.ok || !res.skills) {
                container.innerHTML = `<div class="error">Failed to load skills: ${res.error || 'Unknown error'}</div>`;
                return;
            }

            const names = Object.keys(res.skills);
            if (names.length === 0) {
                container.innerHTML = '<div>No skills registered</div>';
                return;
            }

            names.forEach(name => {
                const versions = res.skills[name] || {};
                Object.keys(versions).forEach(ver => {
                    const skill = versions[ver] || {};
                    const card = document.createElement('div');
                    card.className = 'skill-card';
                    card.innerHTML = `
                        <div class="skill-header">
                            <h3>${name}</h3>
                            <span class="tag">${ver}</span>
                        </div>
                        <p class="skill-desc">${skill.capability || 'No description'}</p>
                        <div class="skill-meta">
                            <strong>Inputs:</strong> ${(skill.inputs || []).join(', ') || 'None'}
                        </div>
                    `;
                    container.appendChild(card);
                });
            });
        };

        loadSkills();

        this.updateHandler = () => {
            loadSkills();
        };
        window.addEventListener('update:skills', this.updateHandler);
    },
    unmount() {
        if (this.updateHandler) {
            window.removeEventListener('update:skills', this.updateHandler);
        }
    }
};
