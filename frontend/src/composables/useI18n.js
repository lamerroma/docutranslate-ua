import { ref } from 'vue';

export function useI18n() {
    const currentLang = ref(localStorage.getItem('ui_language') || 'uk');
    const i18nData = ref({});

    const t = (k, params) => {
        let v = i18nData.value[k] || k;
        if (params) {
            for (const [key, val] of Object.entries(params)) {
                v = v.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val));
            }
        }
        return v;
    };

    const setLanguage = async (l) => {
        currentLang.value = l;
        localStorage.setItem('ui_language', l);
        document.documentElement.lang = l === 'uk' ? 'uk' : 'en';
        // Reload i18n data
        try {
            const res = await fetch(`/static/i18n/${l}.json`);
            i18nData.value = await res.json();
        } catch (e) {
            console.error('Failed to load i18n:', e);
        }
    };

    const loadI18n = async () => {
        try {
            const lang = currentLang.value || 'uk';
            const res = await fetch(`/static/i18n/${lang}.json`);
            i18nData.value = await res.json();
        } catch (e) {
            // Fallback defaults
            i18nData.value = {
                pageTitle: "DocuTranslate",
                tutorialBtn: "Посібник",
                projectContributeBtn: "Співпраця з проектом",
                workflowTitle: "Оберіть сценарій",
                autoWorkflowLabel: "Авто-вибір сценарію",
                workflowOptionPptx: "Презентація PPTX",
                pptxSettingsTitleText: "Параметри перекладу PPTX",
                mineruDeployServerUrlLabel: "URL сервера",
                mineruDeployLangListLabel: "Список мов (режим Pipeline)",
                mineruDeployServerUrlPlaceholder: "http://127.0.0.1:30000",
                mineruDeployParseMethodLabel: "Метод парсингу",
                mineruDeployTableEnableLabel: "Розпізнавання таблиць"
            };
        }
    };

    return {
        currentLang,
        i18nData,
        t,
        setLanguage,
        loadI18n
    };
}
