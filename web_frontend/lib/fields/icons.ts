export type MajorField =
  | 'Natural Sciences'
  | 'Engineering and Technology'
  | 'Medical and Health Sciences'
  | 'Agricultural Sciences'
  | 'Social Sciences and Humanities';

export type SubField =
  | 'Mathematics' | 'Physics' | 'Chemistry' | 'Biology' | 'Earth Science'
  | 'Computer Science' | 'Mechanical Engineering' | 'Electrical Engineering'
  | 'Civil Engineering' | 'Aerospace Engineering'
  | 'General Medicine' | 'Pharmacy' | 'Dentistry' | 'Public Health' | 'Neuroscience'
  | 'Agronomy' | 'Animal Science and Veterinary Medicine' | 'Fisheries' | 'Forestry'
  | 'Economics' | 'Psychology' | 'Sociology' | 'Law' | 'Education' | 'Finance'
  | 'Literature' | 'Linguistics';

export type AllField = MajorField | SubField;

// Map fields to the STRING NAME of their Lucide icon
export const iconNameMap: Record<AllField, string> = {
  // Major groups
  'Natural Sciences': 'Atom',
  'Engineering and Technology': 'Cpu',
  'Medical and Health Sciences': 'HeartPulse',
  'Agricultural Sciences': 'Sprout',
  'Social Sciences and Humanities': 'BookOpen',

  // Natural Sciences
  'Mathematics': 'Sigma',
  'Physics': 'Atom',
  'Chemistry': 'FlaskConical',
  'Biology': 'Microscope',
  'Earth Science': 'Globe',

  // Engineering & Technology
  'Computer Science': 'Monitor',
  'Mechanical Engineering': 'Cog',
  'Electrical Engineering': 'Zap',
  'Civil Engineering': 'Building',
  'Aerospace Engineering': 'Rocket',

  // Medical & Health Sciences
  'Neuroscience': 'Brain',
  'General Medicine': 'Stethoscope',
  'Pharmacy': 'Pill',
  'Dentistry': 'Bone',
  'Public Health': 'Users',

  // Agricultural Sciences
  'Agronomy': 'Sprout',
  'Animal Science and Veterinary Medicine': 'PawPrint',
  'Fisheries': 'Fish',
  'Forestry': 'TreePine',

  // Social Sciences & Humanities
  'Economics': 'TrendingUp',
  'Finance': 'TrendingUp',
  'Psychology': 'Brain',
  'Sociology': 'Users',
  'Law': 'Scale',
  'Education': 'GraduationCap',
  'Literature': 'BookOpen',
  'Linguistics': 'Globe2',
};

// Color theme per major field
const majorColorMap: Record<MajorField, string> = {
  'Natural Sciences': 'bg-purple-50 text-purple-600',
  'Engineering and Technology': 'bg-blue-50 text-blue-600',
  'Medical and Health Sciences': 'bg-rose-50 text-rose-600',
  'Agricultural Sciences': 'bg-green-50 text-green-600',
  'Social Sciences and Humanities': 'bg-amber-50 text-amber-600',
};

function getMajorField(field: AllField): MajorField {
  const subToMajor: Partial<Record<SubField, MajorField>> = {
    'Mathematics': 'Natural Sciences',
    'Physics': 'Natural Sciences',
    'Chemistry': 'Natural Sciences',
    'Biology': 'Natural Sciences',
    'Earth Science': 'Natural Sciences',
    'Computer Science': 'Engineering and Technology',
    'Mechanical Engineering': 'Engineering and Technology',
    'Electrical Engineering': 'Engineering and Technology',
    'Civil Engineering': 'Engineering and Technology',
    'Aerospace Engineering': 'Engineering and Technology',
    'General Medicine': 'Medical and Health Sciences',
    'Pharmacy': 'Medical and Health Sciences',
    'Neuroscience': 'Medical and Health Sciences',
    'Dentistry': 'Medical and Health Sciences',
    'Public Health': 'Medical and Health Sciences',
    'Agronomy': 'Agricultural Sciences',
    'Animal Science and Veterinary Medicine': 'Agricultural Sciences',
    'Fisheries': 'Agricultural Sciences',
    'Forestry': 'Agricultural Sciences',
    'Economics': 'Social Sciences and Humanities',
    'Finance': 'Social Sciences and Humanities',
    'Psychology': 'Social Sciences and Humanities',
    'Sociology': 'Social Sciences and Humanities',
    'Law': 'Social Sciences and Humanities',
    'Education': 'Social Sciences and Humanities',
    'Literature': 'Social Sciences and Humanities',
    'Linguistics': 'Social Sciences and Humanities',
  };
  return (subToMajor[field as SubField] as MajorField) || (field as MajorField);
}

// Helper functions for ProjectCard 

/** Returns the string icon name for a given field. */
export function getIconName(field: string): string {
  return iconNameMap[field as AllField];
}

/** Returns the Tailwind color classes for a given field. */
export function getCategoryColor(field: string): string {
  return majorColorMap[getMajorField(field as AllField)] ?? 'bg-gray-50 text-gray-600';
}

