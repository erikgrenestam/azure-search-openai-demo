import i18next from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import HttpApi from "i18next-http-backend";
import { initReactI18next } from "react-i18next";

import daTranslation from "../locales/da/translation.json";
import enTranslation from "../locales/en/translation.json";


export const supportedLngs: { [key: string]: { name: string; locale: string } } = {
    da: {
        name: "Dansk",
        locale: "da-DK"
    },
    en: {
        name: "English",
        locale: "en-US"
    }
};

i18next
    .use(HttpApi)
    .use(LanguageDetector)
    .use(initReactI18next)
    // init i18next
    // for all options read: https://www.i18next.com/overview/configuration-options
    .init({
        resources: {
            da: { translation: daTranslation },
            en: { translation: enTranslation }
        },
        fallbackLng: "en",
        supportedLngs: Object.keys(supportedLngs),
        debug: import.meta.env.DEV,
        interpolation: {
            escapeValue: false // not needed for react as it escapes by default
        }
    });

export default i18next;
