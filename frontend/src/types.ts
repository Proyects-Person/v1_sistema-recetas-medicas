export type Status = 'pendiente' | 'procesando' | 'procesada' | 'aprobada' | 'observada' | 'cancelada'

export interface User {
  id: number
  email: string
  full_name: string
  role: string
  dni?: string | null
  phone?: string | null
  photo_url?: string | null
  is_active: boolean
  created_at: string
}

export interface Activity {
  id: number
  action: string
  description: string
  created_at: string
}

export interface DictionarySuggestion {
  original: string
  suggestion: string
  category?: string | null
  confidence?: number | null
  reason?: string | null
  mode?: string | null
}

export interface RecognizedTerm {
  term: string
  category?: string | null
  match?: string | null
  confidence?: number | null
  mode?: string | null
}

export interface StructuredMedicationRow {
  medication_or_ingredient?: string | null
  concentration?: string | null
  pharmaceutical_form?: string | null
  quantity?: string | null
  dosage?: string | null
  frequency?: string | null
  duration?: string | null
  administration_route?: string | null
}

export interface Recipe {
  id: number
  code: string
  file_name: string
  status: Status

  raw_text?: string | null
  normalized_text?: string | null

  dictionary_suggestions: DictionarySuggestion[]
  recognized_terms: RecognizedTerm[]

  structured_data: StructuredMedicationRow[]

  ocr_confidence: number
  ocr_engine?: string | null
  low_confidence_fields: string[]

  patient_name?: string | null
  patient_age?: number | null
  patient_phone?: string | null
  service_reason?: string | null

  doctor_name?: string | null
  diagnosis?: string | null

  composition?: string | null
  administration_route?: string | null
  dosage?: string | null

  observations?: string | null

  created_at: string
  updated_at: string

  validated_at?: string | null
  validator_name?: string | null
  created_by_name?: string | null
}

export interface RecipeListItem {
  id: number
  code: string

  file_name?: string | null
  raw_text?: string | null
  normalized_text?: string | null

  patient_name?: string | null
  patient_age?: number | null
  patient_phone?: string | null
  service_reason?: string | null

  doctor_name?: string | null
  composition?: string | null

  status: Status

  ocr_confidence: number
  ocr_engine?: string | null

  created_at: string

  validator_name?: string | null
}

export interface DashboardData {
  pending: number
  processed_week: number
  observed: number
  approved: number
  avg_confidence: number
  total_recipes: number
  recent_recipes: RecipeListItem[]
  activities: Activity[]
}

export interface UserConfig {
  notifications: boolean
  theme: string
  language: string
  updated_at: string
}