/**
 * useDocumentDirection Hook
 * Syncs HTML lang and dir attributes with i18n language changes
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

// Languages that use RTL direction
const RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur'];

export function useDocumentDirection() {
  const { i18n } = useTranslation();

  useEffect(() => {
    const currentLang = i18n.language;
    const isRTL = RTL_LANGUAGES.includes(currentLang);
    const direction = isRTL ? 'rtl' : 'ltr';

    // Update HTML attributes
    document.documentElement.lang = currentLang;
    document.documentElement.dir = direction;

    // Update body class for styling hooks
    document.body.classList.remove('ltr', 'rtl');
    document.body.classList.add(direction);

    // Store direction for CSS variable usage
    document.documentElement.style.setProperty('--direction', direction);
    document.documentElement.style.setProperty('--rtl-multiplier', isRTL ? '-1' : '1');

    return () => {
      // Cleanup not strictly necessary but good practice
      document.body.classList.remove(direction);
    };
  }, [i18n.language]);

  return {
    language: i18n.language,
    direction: RTL_LANGUAGES.includes(i18n.language) ? 'rtl' : 'ltr',
    isRTL: RTL_LANGUAGES.includes(i18n.language),
  };
}

export default useDocumentDirection;
