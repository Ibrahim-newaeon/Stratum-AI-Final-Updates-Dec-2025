import * as React from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

// Common country codes with flags
const COUNTRY_CODES = [
  { code: '+1', country: 'US', flag: '🇺🇸', name: 'United States' },
  { code: '+1', country: 'CA', flag: '🇨🇦', name: 'Canada' },
  { code: '+44', country: 'GB', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+91', country: 'IN', flag: '🇮🇳', name: 'India' },
  { code: '+61', country: 'AU', flag: '🇦🇺', name: 'Australia' },
  { code: '+49', country: 'DE', flag: '🇩🇪', name: 'Germany' },
  { code: '+33', country: 'FR', flag: '🇫🇷', name: 'France' },
  { code: '+81', country: 'JP', flag: '🇯🇵', name: 'Japan' },
  { code: '+86', country: 'CN', flag: '🇨🇳', name: 'China' },
  { code: '+55', country: 'BR', flag: '🇧🇷', name: 'Brazil' },
  { code: '+52', country: 'MX', flag: '🇲🇽', name: 'Mexico' },
  { code: '+34', country: 'ES', flag: '🇪🇸', name: 'Spain' },
  { code: '+39', country: 'IT', flag: '🇮🇹', name: 'Italy' },
  { code: '+82', country: 'KR', flag: '🇰🇷', name: 'South Korea' },
  { code: '+31', country: 'NL', flag: '🇳🇱', name: 'Netherlands' },
  { code: '+46', country: 'SE', flag: '🇸🇪', name: 'Sweden' },
  { code: '+47', country: 'NO', flag: '🇳🇴', name: 'Norway' },
  { code: '+45', country: 'DK', flag: '🇩🇰', name: 'Denmark' },
  { code: '+358', country: 'FI', flag: '🇫🇮', name: 'Finland' },
  { code: '+48', country: 'PL', flag: '🇵🇱', name: 'Poland' },
  { code: '+7', country: 'RU', flag: '🇷🇺', name: 'Russia' },
  { code: '+971', country: 'AE', flag: '🇦🇪', name: 'UAE' },
  { code: '+966', country: 'SA', flag: '🇸🇦', name: 'Saudi Arabia' },
  { code: '+27', country: 'ZA', flag: '🇿🇦', name: 'South Africa' },
  { code: '+234', country: 'NG', flag: '🇳🇬', name: 'Nigeria' },
  { code: '+254', country: 'KE', flag: '🇰🇪', name: 'Kenya' },
  { code: '+20', country: 'EG', flag: '🇪🇬', name: 'Egypt' },
  { code: '+65', country: 'SG', flag: '🇸🇬', name: 'Singapore' },
  { code: '+60', country: 'MY', flag: '🇲🇾', name: 'Malaysia' },
  { code: '+66', country: 'TH', flag: '🇹🇭', name: 'Thailand' },
  { code: '+62', country: 'ID', flag: '🇮🇩', name: 'Indonesia' },
  { code: '+63', country: 'PH', flag: '🇵🇭', name: 'Philippines' },
  { code: '+84', country: 'VN', flag: '🇻🇳', name: 'Vietnam' },
  { code: '+64', country: 'NZ', flag: '🇳🇿', name: 'New Zealand' },
  { code: '+353', country: 'IE', flag: '🇮🇪', name: 'Ireland' },
  { code: '+41', country: 'CH', flag: '🇨🇭', name: 'Switzerland' },
  { code: '+43', country: 'AT', flag: '🇦🇹', name: 'Austria' },
  { code: '+32', country: 'BE', flag: '🇧🇪', name: 'Belgium' },
  { code: '+351', country: 'PT', flag: '🇵🇹', name: 'Portugal' },
  { code: '+30', country: 'GR', flag: '🇬🇷', name: 'Greece' },
  { code: '+90', country: 'TR', flag: '🇹🇷', name: 'Turkey' },
  { code: '+972', country: 'IL', flag: '🇮🇱', name: 'Israel' },
  { code: '+962', country: 'JO', flag: '🇯🇴', name: 'Jordan' },
  { code: '+54', country: 'AR', flag: '🇦🇷', name: 'Argentina' },
  { code: '+56', country: 'CL', flag: '🇨🇱', name: 'Chile' },
  { code: '+57', country: 'CO', flag: '🇨🇴', name: 'Colombia' },
  { code: '+51', country: 'PE', flag: '🇵🇪', name: 'Peru' },
];

interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
}

export function PhoneInput({
  value,
  onChange,
  placeholder = '234 567 8900',
  disabled = false,
  error = false,
  className,
}: PhoneInputProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedCountry, setSelectedCountry] = React.useState(COUNTRY_CODES[0]);
  const [phoneNumber, setPhoneNumber] = React.useState('');
  const [searchQuery, setSearchQuery] = React.useState('');
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Parse initial value
  React.useEffect(() => {
    if (value) {
      // Try to find matching country code
      const matchedCountry = COUNTRY_CODES.find((c) => value.startsWith(c.code));
      if (matchedCountry) {
        setSelectedCountry(matchedCountry);
        setPhoneNumber(value.slice(matchedCountry.code.length).trim());
      } else {
        setPhoneNumber(value.replace(/^\+\d+\s*/, ''));
      }
    }
  }, []);

  // Close dropdown on outside click
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPhone = e.target.value.replace(/[^\d\s-]/g, '');
    setPhoneNumber(newPhone);
    onChange(`${selectedCountry.code} ${newPhone}`.trim());
  };

  const handleCountrySelect = (country: (typeof COUNTRY_CODES)[0]) => {
    setSelectedCountry(country);
    setIsOpen(false);
    setSearchQuery('');
    onChange(`${country.code} ${phoneNumber}`.trim());
  };

  const filteredCountries = COUNTRY_CODES.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.code.includes(searchQuery) ||
      c.country.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className={cn('relative', className)} ref={dropdownRef}>
      <div
        className={cn(
          'flex rounded-xl bg-surface-secondary border-2 transition-all duration-200',
          error ? 'border-danger' : 'border-white/10 focus-within:border-stratum-500/50',
          'focus-within:ring-2',
          error ? 'focus-within:ring-danger/20' : 'focus-within:ring-stratum-500/20',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        {/* Country selector */}
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={cn(
            'flex items-center gap-1.5 px-3 py-3 border-r border-white/10',
            'text-white hover:bg-white/5 transition-colors rounded-l-xl',
            disabled && 'cursor-not-allowed'
          )}
        >
          <span className="text-lg">{selectedCountry.flag}</span>
          <span className="text-sm font-medium text-text-secondary">{selectedCountry.code}</span>
          <ChevronDownIcon
            className={cn('w-4 h-4 text-text-muted transition-transform', isOpen && 'rotate-180')}
          />
        </button>

        {/* Phone input */}
        <input
          type="tel"
          value={phoneNumber}
          onChange={handlePhoneChange}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            'flex-1 px-3 py-3 bg-transparent outline-none',
            'text-white placeholder-text-muted text-body',
            'rounded-r-xl'
          )}
        />
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div
          className={cn(
            'absolute z-50 top-full left-0 mt-2 w-full max-h-64 overflow-hidden',
            'rounded-xl bg-surface-secondary border border-white/10 shadow-xl',
            'animate-fade-in'
          )}
        >
          {/* Search input */}
          <div className="p-2 border-b border-white/10">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search country..."
              autoFocus
              className={cn(
                'w-full px-3 py-2 rounded-lg bg-surface-tertiary border border-white/10',
                'text-white placeholder-text-muted text-sm',
                'outline-none focus:border-stratum-500/50'
              )}
            />
          </div>

          {/* Country list */}
          <div className="overflow-y-auto max-h-48">
            {filteredCountries.length === 0 ? (
              <div className="px-4 py-3 text-sm text-text-muted text-center">No countries found</div>
            ) : (
              filteredCountries.map((country, index) => (
                <button
                  key={`${country.country}-${index}`}
                  type="button"
                  onClick={() => handleCountrySelect(country)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-2.5 text-left',
                    'hover:bg-white/5 transition-colors',
                    selectedCountry.country === country.country &&
                      selectedCountry.code === country.code &&
                      'bg-stratum-500/10'
                  )}
                >
                  <span className="text-lg">{country.flag}</span>
                  <span className="flex-1 text-sm text-white">{country.name}</span>
                  <span className="text-sm text-text-muted">{country.code}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
