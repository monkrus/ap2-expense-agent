import React from 'react';
import { getRoleTheme, getRoleCapabilities } from '../utils/roleThemes';
import { Info } from 'lucide-react';

/**
 * Role Badge Component
 * Displays user's role with icon, color-coding, and optional capabilities tooltip
 */
const RoleBadge = ({ role, size = 'default', showCapabilities = false }) => {
  const theme = getRoleTheme(role);
  const capabilities = getRoleCapabilities(role);

  const sizeClasses = {
    small: 'px-2 py-1 text-xs',
    default: 'px-3 py-1.5 text-sm',
    large: 'px-4 py-2 text-base',
  };

  const [showTooltip, setShowTooltip] = React.useState(false);

  return (
    <div className="relative inline-block">
      <div
        className={`${theme.colors.badge} rounded-full font-semibold ${sizeClasses[size]} flex items-center gap-2 shadow-sm`}
        onMouseEnter={() => showCapabilities && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span className="text-lg">{theme.icon}</span>
        <span>{theme.name}</span>
        {showCapabilities && (
          <Info className="w-4 h-4 opacity-60" />
        )}
      </div>

      {/* Capabilities Tooltip */}
      {showCapabilities && showTooltip && (
        <div className="absolute z-50 top-full left-0 mt-2 w-72 bg-white rounded-lg shadow-xl border-2 border-gray-200 p-4">
          <div className="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-2">
            <span className="text-xl">{theme.icon}</span>
            {theme.name} Capabilities
          </div>
          <div className="text-xs text-gray-600 mb-3 italic">
            {theme.description}
          </div>
          <ul className="space-y-1.5">
            {capabilities.map((capability, index) => (
              <li key={index} className="text-xs text-gray-700 leading-relaxed">
                {capability}
              </li>
            ))}
          </ul>
          <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
            Permissions are managed by the RBAC system
          </div>
        </div>
      )}
    </div>
  );
};

export default RoleBadge;
