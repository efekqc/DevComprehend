# Veri sözleşmeleri
Sözleşmeler DC-002'de makine tarafından doğrulanabilir şemaya dönüştürülecek.
## Temel varlıklar
- Analysis: id, user_id, repository_id, commit_sha, pipeline_version, status, usage.
- Concept: id, analysis_id, name, source_references, assessment_state.
- Question: id, concept_id, prompt, evidence, rubric, difficulty.
- Answer: id, question_id, user_id, text, created_at.
- Evaluation: answer_id, rubric_results, feedback, uncertainty, model_version.
- Review: user_id, concept_id, due_at, last_evaluation_id.

assessment_state: unassessed / developing / demonstrated. Bir puan tek başına tüm teknolojiyi bildiği anlamına gelmez. Kaynak referansları değişmez commit SHA içermelidir. ID ve tarih formatları DC-002'de kesinleşir.
