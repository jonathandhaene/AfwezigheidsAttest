import { createContext, useContext, useState, useEffect } from 'react'
import nlTranslations from './translations/nl.json'
import frTranslations from './translations/fr.json'
import enTranslations from './translations/en.json'

const translations = {
  nl: nlTranslations,
  fr: frTranslations,
  en: enTranslations
}

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    // Load language from localStorage or default to Dutch
    return localStorage.getItem('language') || 'nl'
  })

  useEffect(() => {
    // Save language preference
    localStorage.setItem('language', language)
  }, [language])

  const t = (key, params = {}) => {
    const keys = key.split('.')
    let value = translations[language]
    
    for (const k of keys) {
      value = value?.[k]
    }
    
    if (!value) {
      console.warn(`Translation missing for key: ${key} in language: ${language}`)
      return key
    }
    
    // Replace parameters like {filename}, {size}, etc.
    let result = value
    for (const [param, paramValue] of Object.entries(params)) {
      result = result.replace(`{${param}}`, paramValue)
    }
    
    return result
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useTranslation() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useTranslation must be used within a LanguageProvider')
  }
  return context
}
