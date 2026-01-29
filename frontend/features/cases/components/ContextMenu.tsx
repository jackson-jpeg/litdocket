'use client';

import { useEffect, useRef } from 'react';
import { Archive, FileDown, FileText, Users } from 'lucide-react';

interface ContextMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  onArchive: () => void;
  onExportDetails: () => void;
  onGenerateReport: () => void;
  onAssignAttorney: () => void;
}

export default function ContextMenu({
  x,
  y,
  onClose,
  onArchive,
  onExportDetails,
  onGenerateReport,
  onAssignAttorney,
}: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  const menuItems = [
    {
      label: 'Export Details',
      icon: FileText,
      onClick: onExportDetails,
    },
    {
      label: 'Generate Report',
      icon: FileDown,
      onClick: onGenerateReport,
    },
    {
      label: 'Assign Attorney',
      icon: Users,
      onClick: onAssignAttorney,
    },
    {
      label: 'Archive Case',
      icon: Archive,
      onClick: onArchive,
      danger: true,
    },
  ];

  return (
    <div
      ref={menuRef}
      className="fixed z-50 bg-white rounded-lg shadow-2xl border border-slate-200 py-1 min-w-[180px]"
      style={{ top: y, left: x }}
    >
      {menuItems.map((item, index) => {
        const Icon = item.icon;
        return (
          <button
            key={index}
            onClick={() => {
              item.onClick();
              onClose();
            }}
            className={`
              w-full flex items-center gap-3 px-4 py-2 text-sm text-left
              transition-colors
              ${
                item.danger
                  ? 'text-red-600 hover:bg-red-50'
                  : 'text-slate-700 hover:bg-slate-50'
              }
            `}
          >
            <Icon className="w-4 h-4" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </div>
  );
}
