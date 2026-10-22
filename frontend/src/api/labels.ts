import type { Schemas } from "./client";

export const ROLE_LABELS: Record<Schemas["UserRole"], string> = {
  ceo: "Генеральный директор",
  cfo: "Финансовый директор",
  accountant: "Главный бухгалтер",
  treasurer: "Казначей",
};

export const PROVENANCE: Record<Schemas["Provenance"], { label: string; className: string }> = {
  source_fact: { label: "Факт из источника", className: "bg-fact/10 text-fact ring-fact/30" },
  bank_position: { label: "Позиция Альфа-Банка", className: "bg-bank/10 text-bank ring-bank/30" },
  ai_inference: { label: "Вывод AI", className: "bg-ai/10 text-ai ring-ai/30" },
};

export const STEP_LABELS: Record<Schemas["StepKind"], string> = {
  plan: "План",
  tool_call: "Инструмент",
  draft: "Черновик",
  critic: "Критик",
  retry: "Повтор",
  final: "Итог",
};

export const LEVEL_LABELS: Record<Schemas["Level"], string> = {
  low: "низкий",
  medium: "средний",
  high: "высокий",
};

// Record over the generated enum: a new tag in the taxonomy fails the typecheck until labelled
export const TAG_LABELS: Record<Schemas["SensitivityTag"], string> = {
  key_rate: "Ключевая ставка",
  fx_rate: "Валютный курс",
  inflation: "Инфляция",
  consumer_demand: "Потребительский спрос",
  commodities_energy: "Энергоносители",
  commodities_metals: "Металлы",
  commodities_agri: "Агросырьё",
  gold: "Золото",
  credit_market: "Кредитный рынок",
  bond_market: "Рынок облигаций",
  export_import: "ВЭД",
  sanctions: "Санкции",
  regulation: "Регулирование",
  taxes: "Налоги",
  logistics: "Логистика",
  labor_market: "Рынок труда",
  other: "Прочее",
};

export const JOB_ERRORS: Partial<Record<Schemas["ErrorCode"], string>> = {
  budget_exhausted: "Дневной лимит AI исчерпан. Новые инсайты появятся завтра, готовые доступны в ленте",
  upstream_failed: "Агент не смог построить инсайт",
};
