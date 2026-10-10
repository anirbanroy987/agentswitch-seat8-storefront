# Tools visible to this seat (296 tools, 61 entities)

## AccountPlan
- `AccountPlan.get`(id) Get a single AccountPlan record by ID
- `AccountPlan.list`(limit, offset, search, sort_by, sort_order) List AccountPlan records with optional filters

## Activity
- `Activity.create`(assigned_to, company_id, deal_id, description, done, due_date, due_time, duration, lead_id, outcome, party_id, priority, subject, type) Create a new Activity record
- `Activity.get`(id) Get a single Activity record by ID
- `Activity.list`(assigned_to, company_id, deal_id, done, due_date, due_time, duration, lead_id, limit, offset, outcome, party_id, priority, search, sort_by, sort_order, subject, type) List Activity records with optional filters
- `Activity.update`(assigned_to, company_id, deal_id, description, done, due_date, due_time, duration, id, lead_id, outcome, party_id, priority, subject, type) Update an existing Activity record

## AddressBook
- `AddressBook.create`(color, company_id, description, icon, is_default, is_visible, last_synced_at, name, owner_party_id, sort_order, source, subscription_url, type) Create a new AddressBook record
- `AddressBook.delete`(id) Delete a AddressBook record by ID
- `AddressBook.get`(id) Get a single AddressBook record by ID
- `AddressBook.list`(color, company_id, icon, is_default, is_visible, last_synced_at, limit, name, offset, owner_party_id, search, sort_by, sort_order, source, subscription_url, type) List AddressBook records with optional filters
- `AddressBook.update`(color, company_id, description, icon, id, is_default, is_visible, last_synced_at, name, owner_party_id, sort_order, source, subscription_url, type) Update an existing AddressBook record

## AddressBookEntry
- `AddressBookEntry.create`(added_at, address_book_id, company_id, is_favorite, notes, party_id) Create a new AddressBookEntry record
- `AddressBookEntry.delete`(id) Delete a AddressBookEntry record by ID
- `AddressBookEntry.get`(id) Get a single AddressBookEntry record by ID
- `AddressBookEntry.list`(added_at, address_book_id, company_id, is_favorite, limit, offset, party_id, search, sort_by, sort_order) List AddressBookEntry records with optional filters
- `AddressBookEntry.update`(added_at, address_book_id, company_id, id, is_favorite, notes, party_id) Update an existing AddressBookEntry record

## AgentEscalation
- `AgentEscalation.create`(channel, company_id, party_id, reason, reason_code, resolution_note, session_id, subject) Create a new AgentEscalation record
- `AgentEscalation.get`(id) Get a single AgentEscalation record by ID
- `AgentEscalation.list`(channel, company_id, limit, offset, party_id, reason_code, search, session_id, sort_by, sort_order, subject) List AgentEscalation records with optional filters
- `AgentEscalation.update`(channel, company_id, id, party_id, reason, reason_code, resolution_note, session_id, subject) Update an existing AgentEscalation record

## AgentFloorConfig
- `AgentFloorConfig.get`(id) Get a single AgentFloorConfig record by ID
- `AgentFloorConfig.list`(company_id, dedupe_window_minutes, global_concurrency, limit, max_chain_depth, name, offset, paused, paused_at, paused_by, paused_reason, per_persona_concurrency, poll_seconds, search, sort_by, sort_order) List AgentFloorConfig records with optional filters

## AgentJob
- `AgentJob.get`(id) Get a single AgentJob record by ID
- `AgentJob.list`(approval_request_id, awaiting_deadline, awaiting_job_ids, chain_depth, company_id, correlation_id, dedupe_key, duration_ms, error, evaluation_decision, finished_at, goal_args, goal_key, limit, llm_cost, offset, parent_job_id, persona_id, priority, queued_at, requires_plan, retry_count, retry_of, search, session_id, sort_by, sort_order, started_at, status, title, tokens_used, trigger_entity, trigger_id, trigger_kind, trigger_label, user_id) List AgentJob records with optional filters

## AgentJobStep
- `AgentJobStep.get`(id) Get a single AgentJobStep record by ID
- `AgentJobStep.list`(duration_ms, entity, job_id, kind, limit, offset, ok, record_id, search, seq, sort_by, sort_order, summary, tool_name) List AgentJobStep records with optional filters

## AgentLedgerSeal
- `AgentLedgerSeal.get`(id) Get a single AgentLedgerSeal record by ID
- `AgentLedgerSeal.list`(chain_head, company_id, correlation_id, event_count, events_digest, first_seq, job_id, last_seq, limit, offset, payload_version, prev_chain_head, prev_seal_id, scope, seal_reason, sealed_at, sealed_by, search, signature, signature_alg, signature_key_label, sort_by, sort_order) List AgentLedgerSeal records with optional filters

## AgentMemory
- `AgentMemory.create`(category, company_id, content, expires_at, importance, is_active, party_id, session_id, source, user_id) Create a new AgentMemory record
- `AgentMemory.get`(id) Get a single AgentMemory record by ID
- `AgentMemory.list`(category, company_id, expires_at, importance, is_active, limit, offset, party_id, search, session_id, sort_by, sort_order, source, user_id) List AgentMemory records with optional filters
- `AgentMemory.update`(category, company_id, content, expires_at, id, importance, is_active, party_id, session_id, source, user_id) Update an existing AgentMemory record

## AgentMessage
- `AgentMessage.get`(id) Get a single AgentMessage record by ID
- `AgentMessage.list`(cached_input_tokens, company_id, error, input_tokens, latency_ms, limit, llm_cost, offset, output_tokens, provider_id, role, search, session_id, sort_by, sort_order, tool_call_id, tool_name, tool_status, user_id) List AgentMessage records with optional filters

## AgentPersona
- `AgentPersona.daily_limits`() Tokens and USD spend each agent persona you can see has used today against its daily limits (tokens_used_today / daily_token_budget, spend_today_usd / daily_llm_budget_usd), what remains, whether it is blocked, when the limits reset (00:00 UTC), and totals. Read-only; only an admin can change a limit.
- `AgentPersona.get`(id) Get a single AgentPersona record by ID
- `AgentPersona.list`(active_skill_id, board_order, color, company_id, daily_job_cap, domains, icon, is_active, is_default, is_worker, limit, mailbox_id, max_tool_calls, name, offset, provider_id, require_plan, search, sla_target_minutes, sort_by, sort_order, tool_policy_id, user_id) List AgentPersona records with optional filters

## AgentPrivacyEvent
- `AgentPrivacyEvent.get`(id) Get a single AgentPrivacyEvent record by ID
- `AgentPrivacyEvent.list`(actor_display, actor_user_id, basis_code, company_id, erased_digest, kind, limit, memories_erased, offset, payload_version, privacy_class, retain_until, retention_rule_id, search, session_id, signature, signature_alg, signature_key_label, sort_by, sort_order) List AgentPrivacyEvent records with optional filters

## AgentProvider
- `AgentProvider.get`(id) Get a single AgentProvider record by ID
- `AgentProvider.list`(api_key_ref, company_id, endpoint, is_active, is_default, limit, max_tokens, model, name, offset, provider, search, sort_by, sort_order, supports_tools, supports_vision, temperature) List AgentProvider records with optional filters

## AgentRetentionRule
- `AgentRetentionRule.get`(id) Get a single AgentRetentionRule record by ID
- `AgentRetentionRule.list`(company_id, erase_memories, is_active, limit, name, offset, privacy_class, redact_session_labels, retain_days, search, sort_by, sort_order) List AgentRetentionRule records with optional filters

## AgentRunbook
- `AgentRunbook.get`(id) Get a single AgentRunbook record by ID
- `AgentRunbook.list`(company_id, failure_signature, limit, name, offset, persona_id, required_role, search, sort_by, sort_order, status) List AgentRunbook records with optional filters

## AgentRunbookRun
- `AgentRunbookRun.get`(id) Get a single AgentRunbookRun record by ID
- `AgentRunbookRun.list`(actor, actor_roles, approval_request_id, at, company_id, correlation_id, job_id, limit, mode, offset, outcome, reason_code, runbook_id, runbook_name, search, sort_by, sort_order, steps_digest) List AgentRunbookRun records with optional filters

## AgentSeat
- `AgentSeat.get`(id) Get a single AgentSeat record by ID
- `AgentSeat.list`(app, color, company_id, goal_keys, icon, is_active, limit, module, name, offset, persona_id, search, seat_number, sort_by, sort_order, tier, user_id) List AgentSeat records with optional filters

## AgentSession
- `AgentSession.close.active.closed`(id) Transition AgentSession from 'active' to 'closed'
- `AgentSession.close.idle.closed`(id) Transition AgentSession from 'idle' to 'closed'
- `AgentSession.create`(actor_kind, actor_label, actor_roles, actor_user_id, channel, channel_conversation_id, company_id, estimated_cost, last_message_at, message_count, metadata, party_id, persona_id, provider_id, skill_id, skill_version, status, title, tool_policy_id, total_input_tokens, total_output_tokens, total_tool_calls) Create a new AgentSession record
- `AgentSession.get`(id) Get a single AgentSession record by ID
- `AgentSession.list`(actor_kind, actor_label, actor_roles, actor_user_id, channel, channel_conversation_id, company_id, estimated_cost, last_message_at, limit, message_count, offset, party_id, persona_id, provider_id, search, skill_id, skill_version, sort_by, sort_order, status, title, tool_policy_id, total_input_tokens, total_output_tokens, total_tool_calls) List AgentSession records with optional filters
- `AgentSession.pause`(id) Transition AgentSession from 'active' to 'idle'
- `AgentSession.resume`(id) Transition AgentSession from 'idle' to 'active'
- `AgentSession.update`(actor_kind, actor_label, actor_roles, actor_user_id, channel, channel_conversation_id, company_id, estimated_cost, id, last_message_at, message_count, metadata, party_id, persona_id, provider_id, skill_id, skill_version, title, tool_policy_id, total_input_tokens, total_output_tokens, total_tool_calls) Update an existing AgentSession record

## AgentSkill
- `AgentSkill.get`(id) Get a single AgentSkill record by ID
- `AgentSkill.list`(agent_persona_id, change_note, company_id, is_active, limit, name, offset, published_at, search, sort_by, sort_order, summary, supersedes_id, user_id, version) List AgentSkill records with optional filters

## AgentTask
- `AgentTask.complete`(id) Transition AgentTask from 'active' to 'completed'
- `AgentTask.create`(channel, company_id, cron_expression, description, interval_minutes, last_run_at, last_run_error, last_run_error_kind, last_run_session_id, last_run_status, max_retries, name, next_run_at, notify_on_success, notify_party_id, persona_id, plan, prompt, provider_id, run_count, schedule_type, status, timeout_seconds, user_id) Create a new AgentTask record
- `AgentTask.fail`(id) Transition AgentTask from 'active' to 'failed'
- `AgentTask.get`(id) Get a single AgentTask record by ID
- `AgentTask.list`(channel, company_id, cron_expression, interval_minutes, last_run_at, last_run_error, last_run_error_kind, last_run_session_id, last_run_status, limit, max_retries, name, next_run_at, notify_on_success, notify_party_id, offset, persona_id, provider_id, run_count, schedule_type, search, sort_by, sort_order, status, timeout_seconds, user_id) List AgentTask records with optional filters
- `AgentTask.pause`(id) Transition AgentTask from 'active' to 'paused'
- `AgentTask.resume`(id) Transition AgentTask from 'paused' to 'active'
- `AgentTask.run_now`(id) Run an agent task immediately.
- `AgentTask.update`(channel, company_id, cron_expression, description, id, interval_minutes, last_run_at, last_run_error, last_run_error_kind, last_run_session_id, last_run_status, max_retries, name, next_run_at, notify_on_success, notify_party_id, persona_id, plan, prompt, provider_id, run_count, schedule_type, timeout_seconds, user_id) Update an existing AgentTask record

## AgentTodo
- `AgentTodo.create`(company_id, detail, due_date, persona_id, priority, status, title, written_by) Create a new AgentTodo record
- `AgentTodo.get`(id) Get a single AgentTodo record by ID
- `AgentTodo.list`(company_id, due_date, limit, offset, persona_id, priority, search, sort_by, sort_order, status, title, written_by) List AgentTodo records with optional filters
- `AgentTodo.update`(company_id, detail, due_date, id, persona_id, priority, status, title, written_by) Update an existing AgentTodo record

## AgentToolPolicy
- `AgentToolPolicy.get`(id) Get a single AgentToolPolicy record by ID
- `AgentToolPolicy.list`(allowed_actions, allowed_domains, allowed_entities, company_id, denied_actions, denied_domains, denied_entities, description, is_active, limit, max_records_per_query, name, offset, read_only, risk_mode, role, search, sort_by, sort_order, write_domains) List AgentToolPolicy records with optional filters

## BugReport
- `BugReport.create`(agent_seat, app_version, company_id, delivery, description, issue_number, issue_url, job_id, page, reporter, resolution_note, status) Create a new BugReport record
- `BugReport.get`(id) Get a single BugReport record by ID
- `BugReport.list`(agent_seat, app_version, company_id, delivery, description, issue_number, issue_url, job_id, limit, offset, page, reporter, resolution_note, search, sort_by, sort_order, status) List BugReport records with optional filters

## CRMPreferences
- `CRMPreferences.create`(assignment_method, auto_assign_leads, auto_create_deal_on_lead_convert, company_id, deal_rot_days, default_currency, default_deal_pipeline, enable_activity_reminders, enable_email_tracking, enable_web_to_lead, fiscal_year_start, lead_score_threshold, lead_scoring_enabled, reminder_before_hours) Create a new CRMPreferences record
- `CRMPreferences.get`(id) Get a single CRMPreferences record by ID
- `CRMPreferences.list`(assignment_method, auto_assign_leads, auto_create_deal_on_lead_convert, company_id, deal_rot_days, default_currency, default_deal_pipeline, enable_activity_reminders, enable_email_tracking, enable_web_to_lead, fiscal_year_start, lead_score_threshold, lead_scoring_enabled, limit, offset, reminder_before_hours, search, sort_by, sort_order) List CRMPreferences records with optional filters
- `CRMPreferences.update`(assignment_method, auto_assign_leads, auto_create_deal_on_lead_convert, company_id, deal_rot_days, default_currency, default_deal_pipeline, enable_activity_reminders, enable_email_tracking, enable_web_to_lead, fiscal_year_start, id, lead_score_threshold, lead_scoring_enabled, reminder_before_hours) Update an existing CRMPreferences record

## CallNoteDraft
- `CallNoteDraft.get`(id) Get a single CallNoteDraft record by ID
- `CallNoteDraft.list`(limit, offset, search, sort_by, sort_order) List CallNoteDraft records with optional filters

## CampaignAudience
- `CampaignAudience.create`(campaign_id, company_id, name, named_exclusions) Create a new CampaignAudience record
- `CampaignAudience.get`(id) Get a single CampaignAudience record by ID
- `CampaignAudience.list`(campaign_id, company_id, limit, name, offset, search, sort_by, sort_order) List CampaignAudience records with optional filters
- `CampaignAudience.update`(campaign_id, company_id, id, name, named_exclusions) Update an existing CampaignAudience record

## Company
- `Company.get`(id) Get a single Company record by ID
- `Company.list`(country, default_currency, fiscal_year_start, limit, name, offset, party_id, sales_order_confirmation, search, sort_by, sort_order) List Company records with optional filters

## ContactGroup
- `ContactGroup.create`(address_book_id, color, company_id, description, member_count, name) Create a new ContactGroup record
- `ContactGroup.delete`(id) Delete a ContactGroup record by ID
- `ContactGroup.get`(id) Get a single ContactGroup record by ID
- `ContactGroup.list`(address_book_id, color, company_id, limit, member_count, name, offset, search, sort_by, sort_order) List ContactGroup records with optional filters
- `ContactGroup.update`(address_book_id, color, company_id, description, id, member_count, name) Update an existing ContactGroup record

## ContactGroupMember
- `ContactGroupMember.create`(added_at, group_id, party_id) Create a new ContactGroupMember record
- `ContactGroupMember.delete`(id) Delete a ContactGroupMember record by ID
- `ContactGroupMember.get`(id) Get a single ContactGroupMember record by ID
- `ContactGroupMember.list`(added_at, group_id, limit, offset, party_id, search, sort_by, sort_order) List ContactGroupMember records with optional filters
- `ContactGroupMember.update`(added_at, group_id, id, party_id) Update an existing ContactGroupMember record

## Coupon
- `Coupon.create`(code, company_id, description, is_active, max_discount, min_order_amount, per_customer_limit, type, usage_limit, used_count, valid_from, valid_to, value) Create a new Coupon record
- `Coupon.get`(id) Get a single Coupon record by ID
- `Coupon.list`(code, company_id, description, is_active, limit, max_discount, min_order_amount, offset, per_customer_limit, search, sort_by, sort_order, type, usage_limit, used_count, valid_from, valid_to, value) List Coupon records with optional filters
- `Coupon.update`(code, company_id, description, id, is_active, max_discount, min_order_amount, per_customer_limit, type, usage_limit, used_count, valid_from, valid_to, value) Update an existing Coupon record

## Deal
- `Deal.create`(company_id, contact_id, currency, expected_close_date, lead_id, lost_reason, notes, owner, party_id, pipeline, probability, products, source, stage, title, value) Create a new Deal record
- `Deal.get`(id) Get a single Deal record by ID
- `Deal.list`(company_id, contact_id, currency, expected_close_date, lead_id, limit, lost_reason, offset, owner, party_id, pipeline, probability, search, sort_by, sort_order, source, stage, title, value) List Deal records with optional filters
- `Deal.make.Quotation`(currency_code, date, expiry_date, gst_no, gst_treatment, id, is_reverse_charge, items, notes, party_id, place_of_supply, project_id, reference_number, tax_computation_note, taxes, terms, valid_till) Create a Quotation from a Deal through its document chain; optional fields override the mapped values.
- `Deal.mark_lost.negotiation.closed_lost`(id) Transition Deal from 'negotiation' to 'closed_lost'
- `Deal.mark_lost.new.closed_lost`(id) Transition Deal from 'new' to 'closed_lost'
- `Deal.mark_lost.proposal.closed_lost`(id) Transition Deal from 'proposal' to 'closed_lost'
- `Deal.mark_lost.qualification.closed_lost`(id) Transition Deal from 'qualification' to 'closed_lost'
- `Deal.mark_won.negotiation.closed_won`(id) Transition Deal from 'negotiation' to 'closed_won'
- `Deal.mark_won.proposal.closed_won`(id) Transition Deal from 'proposal' to 'closed_won'
- `Deal.mark_won.qualification.closed_won`(id) Transition Deal from 'qualification' to 'closed_won'
- `Deal.negotiate`(id) Transition Deal from 'proposal' to 'negotiation'
- `Deal.qualify`(id) Transition Deal from 'new' to 'qualification'
- `Deal.send_proposal`(id) Transition Deal from 'qualification' to 'proposal'
- `Deal.update`(company_id, contact_id, currency, expected_close_date, id, lead_id, lost_reason, notes, owner, party_id, pipeline, probability, products, source, title, value) Update an existing Deal record

## FileAttachment
- `FileAttachment.create`(company_id, content_hash, current_revision_id, current_revision_number, description, download_count, entity_id, entity_type, filename, folder_id, from_email, from_name, is_archived, is_inline, message_subject, mime_type, party_id, received_at, size_bytes, storage_path, tags, thread_id, thumbnail_path) Create a new FileAttachment record
- `FileAttachment.get`(id) Get a single FileAttachment record by ID
- `FileAttachment.list`(company_id, content_hash, current_revision_id, current_revision_number, description, download_count, entity_id, entity_type, filename, folder_id, from_email, from_name, is_archived, is_inline, limit, message_subject, mime_type, offset, party_id, received_at, search, size_bytes, sort_by, sort_order, storage_path, tags, thread_id, thumbnail_path) List FileAttachment records with optional filters
- `FileAttachment.update`(company_id, content_hash, current_revision_id, current_revision_number, description, download_count, entity_id, entity_type, filename, folder_id, from_email, from_name, id, is_archived, is_inline, message_subject, mime_type, party_id, received_at, size_bytes, storage_path, tags, thread_id, thumbnail_path) Update an existing FileAttachment record

## Goal
- `Goal.get`(id) Get a single Goal record by ID
- `Goal.list`(company_id, current_value, end_date, limit, name, offset, owner, period, search, sort_by, sort_order, start_date, target_value, type) List Goal records with optional filters

## HarnessRun
- `HarnessRun.get_run`(run_id) Read one of your team's harness runs by id, including per-task results and the redacted log excerpt.
- `HarnessRun.list_mine`() List your team's harness runs (newest first) with status, score and per-task results, and when your team may submit again.

## Item
- `Item.create`(category_id, code, company_id, default_rate, description, hsn_or_sac, images, inter_state_tax, inter_state_tax_rate, intra_state_tax, intra_state_tax_rate, is_featured, is_published, is_purchasable, is_sellable, is_stock_item, long_description, mrp, name, preferred_vendor_id, product_type, purchase_account, purchase_description, sales_account, selling_price, short_description, sku, slug, sort_order, status, suppliers, tax_code, tax_exemption_reason, tax_preference, taxable, type, uom, variants, weight, weight_unit) Create a new Item record
- `Item.get`(id) Get a single Item record by ID
- `Item.list`(category_id, code, company_id, default_rate, hsn_or_sac, inter_state_tax, inter_state_tax_rate, intra_state_tax, intra_state_tax_rate, is_featured, is_published, is_purchasable, is_sellable, is_stock_item, limit, mrp, name, offset, preferred_vendor_id, product_type, purchase_account, purchase_description, sales_account, search, selling_price, short_description, sku, slug, sort_by, sort_order, status, tax_code, tax_exemption_reason, tax_preference, taxable, type, uom, weight, weight_unit) List Item records with optional filters
- `Item.update`(category_id, code, company_id, default_rate, description, hsn_or_sac, id, images, inter_state_tax, inter_state_tax_rate, intra_state_tax, intra_state_tax_rate, is_featured, is_published, is_purchasable, is_sellable, is_stock_item, long_description, mrp, name, preferred_vendor_id, product_type, purchase_account, purchase_description, sales_account, selling_price, short_description, sku, slug, sort_order, status, suppliers, tax_code, tax_exemption_reason, tax_preference, taxable, type, uom, variants, weight, weight_unit) Update an existing Item record

## Lead
- `Lead.contact`(id) Transition Lead from 'new' to 'contacted'
- `Lead.convert`(id) Transition Lead from 'qualified' to 'converted'
- `Lead.create`(company_id, next_action, notes, party_id, source, status, value) Create a new Lead record
- `Lead.disqualify.contacted.disqualified`(id) Transition Lead from 'contacted' to 'disqualified'
- `Lead.disqualify.new.disqualified`(id) Transition Lead from 'new' to 'disqualified'
- `Lead.disqualify.qualified.disqualified`(id) Transition Lead from 'qualified' to 'disqualified'
- `Lead.get`(id) Get a single Lead record by ID
- `Lead.list`(company_id, limit, next_action, offset, party_id, search, sort_by, sort_order, source, status, value) List Lead records with optional filters
- `Lead.make.Deal`(contact_id, currency, expected_close_date, id, lost_reason, notes, owner, party_id, pipeline, probability, products, source, title, value) Create a Deal from a Lead through its document chain; optional fields override the mapped values.
- `Lead.qualify`(id) Transition Lead from 'contacted' to 'qualified'
- `Lead.update`(company_id, id, next_action, notes, party_id, source, value) Update an existing Lead record

## LedgerRetentionEvent
- `LedgerRetentionEvent.get`(id) Get a single LedgerRetentionEvent record by ID
- `LedgerRetentionEvent.list`(applied_at, applied_by, applied_by_label, company_id, job_id, limit, offset, payload_version, policy_id, reason_code, redacted_count, redactions_digest, search, signature, signature_alg, signature_key_label, sort_by, sort_order, tier) List LedgerRetentionEvent records with optional filters

## LedgerRetentionPolicy
- `LedgerRetentionPolicy.get`(id) Get a single LedgerRetentionPolicy record by ID
- `LedgerRetentionPolicy.list`(company_id, description, enabled, limit, name, offset, search, sensitive_retention_days, sort_by, sort_order) List LedgerRetentionPolicy records with optional filters

## Note
- `Note.create`(company_id, content, deal_id, lead_id, party_id, pinned, title) Create a new Note record
- `Note.get`(id) Get a single Note record by ID
- `Note.list`(company_id, deal_id, lead_id, limit, offset, party_id, pinned, search, sort_by, sort_order, title) List Note records with optional filters
- `Note.update`(company_id, content, deal_id, id, lead_id, party_id, pinned, title) Update an existing Note record

## Notification
- `Notification.get`(id) Get a single Notification record by ID
- `Notification.list`(channel, company_id, entity_id, entity_type, is_read, limit, message, offset, recipient, search, sort_by, sort_order, title, type) List Notification records with optional filters

## Party
- `Party.create`(addresses, anniversary, backup_withholding, bank_details, birthday, company_id, company_name, contact_type, contacts, credit_limit, currency_id, customer_code, customer_sub_type, email, exempt_payee_code, facebook, fatca_exemption_code, first_name, form_1099_box, form_1099_type, gst_treatment, image, is_1099_vendor, is_msme, is_portal_enabled, job_title, last_name, msme_type, name, nickname, opening_balance, owner_name, payment_terms, payment_terms_label, phone, photo_url, place_of_supply, portal_enabled, prefix, pronouns, roles, salutation, suffix, tags, tax_exemption_reason, tax_name, taxable, tin_type, twitter, type, us_tax_classification, vcard_rev, vcard_uid, vendor_bank_code, vendor_bank_name, w9_on_file, w9_received_date, website) Create a new Party record
- `Party.get`(id) Get a single Party record by ID
- `Party.list`(anniversary, backup_withholding, birthday, company_id, company_name, contact_type, credit_limit, currency_id, customer_code, customer_sub_type, email, exempt_payee_code, facebook, fatca_exemption_code, first_name, form_1099_box, form_1099_type, gst_treatment, image, is_1099_vendor, is_msme, is_portal_enabled, job_title, last_name, limit, msme_type, name, nickname, offset, opening_balance, owner_name, payment_terms, payment_terms_label, phone, photo_url, place_of_supply, portal_enabled, prefix, pronouns, salutation, search, sort_by, sort_order, suffix, tax_exemption_reason, tax_name, taxable, tin_type, twitter, type, us_tax_classification, vcard_rev, vcard_uid, vendor_bank_code, vendor_bank_name, w9_on_file, w9_received_date, website) List Party records with optional filters
- `Party.update`(addresses, anniversary, backup_withholding, bank_details, birthday, company_id, company_name, contact_type, contacts, credit_limit, currency_id, customer_code, customer_sub_type, email, exempt_payee_code, facebook, fatca_exemption_code, first_name, form_1099_box, form_1099_type, gst_treatment, id, image, is_1099_vendor, is_msme, is_portal_enabled, job_title, last_name, msme_type, name, nickname, opening_balance, owner_name, payment_terms, payment_terms_label, phone, photo_url, place_of_supply, portal_enabled, prefix, pronouns, roles, salutation, suffix, tags, tax_exemption_reason, tax_name, taxable, tin_type, twitter, type, us_tax_classification, vcard_rev, vcard_uid, vendor_bank_code, vendor_bank_name, w9_on_file, w9_received_date, website) Update an existing Party record

## PartyRelationship
- `PartyRelationship.create`(company_id, from_party_id, is_active, is_primary, notes, relationship, since, to_party_id, until) Create a new PartyRelationship record
- `PartyRelationship.get`(id) Get a single PartyRelationship record by ID
- `PartyRelationship.list`(company_id, from_party_id, is_active, is_primary, limit, notes, offset, relationship, search, since, sort_by, sort_order, to_party_id, until) List PartyRelationship records with optional filters
- `PartyRelationship.update`(company_id, from_party_id, id, is_active, is_primary, notes, relationship, since, to_party_id, until) Update an existing PartyRelationship record

## Pipeline
- `Pipeline.get`(id) Get a single Pipeline record by ID
- `Pipeline.list`(company_id, key, limit, name, offset, search, sort_by, sort_order) List Pipeline records with optional filters

## Plugin
- `Plugin.get`(id) Get a single Plugin record by ID
- `Plugin.list`(action_count, author, disabled_at, enabled_at, endpoint_count, file_hash_sha256, frontend_extension_count, homepage_url, icon, icon_url, installed_at, is_platform, last_error, limit, name, offset, reviewed_at, reviewed_by_user_id, schema_count, script_count, search, slug, sort_by, sort_order, source, source_url, status, uninstalled_at, version) List Plugin records with optional filters

## PricingRule
- `PricingRule.create`(applicable_on, category_id, company_id, discount_amount, discount_percentage, fixed_price, is_active, item_id, min_qty, name, priority, type, valid_from, valid_to) Create a new PricingRule record
- `PricingRule.get`(id) Get a single PricingRule record by ID
- `PricingRule.list`(applicable_on, category_id, company_id, discount_amount, discount_percentage, fixed_price, is_active, item_id, limit, min_qty, name, offset, priority, search, sort_by, sort_order, type, valid_from, valid_to) List PricingRule records with optional filters
- `PricingRule.update`(applicable_on, category_id, company_id, discount_amount, discount_percentage, fixed_price, id, is_active, item_id, min_qty, name, priority, type, valid_from, valid_to) Update an existing PricingRule record

## PrivacyAuditEvent
- `PrivacyAuditEvent.get`(id) Get a single PrivacyAuditEvent record by ID
- `PrivacyAuditEvent.list`(actor_display, actor_user_id, basis_code, company_id, content_digest, entities_denied, entities_scanned, erase_not_before, kind, limit, offset, outcome_code, party_id, payload_version, records_found, request_id, request_type, search, signature, signature_alg, signature_key_label, sort_by, sort_order) List PrivacyAuditEvent records with optional filters

## PrivacyRequest
- `PrivacyRequest.create`(assigned_to, company_id, notes, party_id, received_at, request_type, subject_channel, subject_reference) Create a new PrivacyRequest record
- `PrivacyRequest.get`(id) Get a single PrivacyRequest record by ID
- `PrivacyRequest.list`(assigned_to, company_id, limit, offset, party_id, received_at, request_type, search, sort_by, sort_order, subject_channel, subject_reference) List PrivacyRequest records with optional filters
- `PrivacyRequest.update`(assigned_to, company_id, id, notes, party_id, received_at, request_type, subject_channel, subject_reference) Update an existing PrivacyRequest record

## ProductCategory
- `ProductCategory.create`(company_id, description, image_url, is_active, name, parent_category_id, slug, sort_order) Create a new ProductCategory record
- `ProductCategory.get`(id) Get a single ProductCategory record by ID
- `ProductCategory.list`(company_id, description, image_url, is_active, limit, name, offset, parent_category_id, search, slug, sort_by, sort_order) List ProductCategory records with optional filters
- `ProductCategory.update`(company_id, description, id, image_url, is_active, name, parent_category_id, slug, sort_order) Update an existing ProductCategory record

## Quotation
- `Quotation.accept.sent.accepted`(id) Transition Quotation from 'sent' to 'accepted'
- `Quotation.accept.viewed.accepted`(id) Transition Quotation from 'viewed' to 'accepted'
- `Quotation.convert_to_order.accepted.converted`(id) Transition Quotation from 'accepted' to 'converted'
- `Quotation.convert_to_order.sent.converted`(id) Transition Quotation from 'sent' to 'converted'
- `Quotation.convert_to_order.viewed.converted`(id) Transition Quotation from 'viewed' to 'converted'
- `Quotation.create`(company_id, currency_code, date, deal_id, expiry_date, gst_no, gst_treatment, is_reverse_charge, items, notes, party_id, place_of_supply, project_id, reference_number, status, tax_computation_note, taxes, terms, valid_till) Create a new Quotation record
- `Quotation.decline.sent.declined`(id) Transition Quotation from 'sent' to 'declined'
- `Quotation.decline.viewed.declined`(id) Transition Quotation from 'viewed' to 'declined'
- `Quotation.get`(id) Get a single Quotation record by ID
- `Quotation.list`(company_id, currency_code, date, deal_id, expiry_date, grand_total, gst_no, gst_treatment, is_reverse_charge, limit, net_total, notes, offset, party_id, place_of_supply, project_id, reference_number, search, sort_by, sort_order, status, tax_computation_note, terms, total_tax, valid_till) List Quotation records with optional filters
- `Quotation.make.SalesOrder`(approval_status, date, delivered_status, delivery_date, delivery_method, destination_of_supply, expected_shipment_date, gst_no, gst_treatment, id, invoiced_status, is_reverse_charge, items, nature_of_collection, notes, party_id, payment_gateway, payment_terms, place_of_supply, reference_number, retention_amount, source_of_supply, tax_computation_note, taxes, tcs_amount, tcs_percentage, tcs_tax_name, tds_amount, tds_name, tds_percentage, tds_section, tds_section_code, terms) Create a SalesOrder from a Quotation through its document chain; optional fields override the mapped values.
- `Quotation.release_approved_quote`(id) Transition Quotation from 'pending_approval' to 'sent'
- `Quotation.revise_quote`(id) Transition Quotation from 'pending_approval' to 'draft'
- `Quotation.send`(id) Transition Quotation from 'draft' to 'sent'
- `Quotation.submit_for_margin_approval.draft.pending_approval`(id) Transition Quotation from 'draft' to 'pending_approval'
- `Quotation.submit_for_margin_approval.sent.pending_approval`(id) Transition Quotation from 'sent' to 'pending_approval'
- `Quotation.submit_for_margin_approval.viewed.pending_approval`(id) Transition Quotation from 'viewed' to 'pending_approval'
- `Quotation.update`(company_id, currency_code, date, deal_id, expiry_date, gst_no, gst_treatment, id, is_reverse_charge, items, notes, party_id, place_of_supply, project_id, reference_number, tax_computation_note, taxes, terms, valid_till) Update an existing Quotation record

## SalesOrder
- `SalesOrder.approval.submit`(id) Submit a SalesOrder for approval (approval_status -> pending_approval).
- `SalesOrder.confirm`(id) Transition SalesOrder from 'draft' to 'confirmed'
- `SalesOrder.create`(approval_status, company_id, date, delivered_status, delivery_date, delivery_method, destination_of_supply, expected_shipment_date, gst_no, gst_treatment, invoiced_status, is_reverse_charge, items, nature_of_collection, notes, party_id, payment_gateway, payment_terms, place_of_supply, quotation_id, reference_number, retention_amount, source_of_supply, status, tax_computation_note, taxes, tcs_amount, tcs_percentage, tcs_tax_name, tds_amount, tds_name, tds_percentage, tds_section, tds_section_code, terms) Create a new SalesOrder record
- `SalesOrder.get`(id) Get a single SalesOrder record by ID
- `SalesOrder.list`(approval_status, company_id, date, delivered_status, delivery_date, delivery_method, destination_of_supply, expected_shipment_date, grand_total, gst_no, gst_treatment, invoiced_status, is_reverse_charge, limit, nature_of_collection, net_total, notes, offset, party_id, payment_gateway, payment_terms, place_of_supply, quotation_id, reference_number, retention_amount, search, sort_by, sort_order, source_of_supply, status, tax_computation_note, tcs_amount, tcs_percentage, tcs_tax_name, tds_amount, tds_name, tds_percentage, tds_section, tds_section_code, terms, total_tax) List SalesOrder records with optional filters
- `SalesOrder.update`(approval_status, company_id, date, delivered_status, delivery_date, delivery_method, destination_of_supply, expected_shipment_date, gst_no, gst_treatment, id, invoiced_status, is_reverse_charge, items, nature_of_collection, notes, party_id, payment_gateway, payment_terms, place_of_supply, quotation_id, reference_number, retention_amount, source_of_supply, tax_computation_note, taxes, tcs_amount, tcs_percentage, tcs_tax_name, tds_amount, tds_name, tds_percentage, tds_section, tds_section_code, terms) Update an existing SalesOrder record

## ShippingMethod
- `ShippingMethod.create`(base_rate, company_id, description, estimated_days_max, estimated_days_min, free_above, is_active, name, sort_order) Create a new ShippingMethod record
- `ShippingMethod.get`(id) Get a single ShippingMethod record by ID
- `ShippingMethod.list`(base_rate, company_id, description, estimated_days_max, estimated_days_min, free_above, is_active, limit, name, offset, search, sort_by, sort_order) List ShippingMethod records with optional filters
- `ShippingMethod.update`(base_rate, company_id, description, estimated_days_max, estimated_days_min, free_above, id, is_active, name, sort_order) Update an existing ShippingMethod record

## StockAlert
- `StockAlert.get`(id) Get a single StockAlert record by ID
- `StockAlert.list`(company_id, email, item_id, limit, offset, party_id, search, sort_by, sort_order, variant_sku) List StockAlert records with optional filters
- `StockAlert.update`(company_id, email, id, item_id, party_id, variant_sku) Update an existing StockAlert record

## StorefrontSettings
- `StorefrontSettings.get`(id) Get a single StorefrontSettings record by ID
- `StorefrontSettings.list`(apply_pricing_rules, company_id, limit, logo_url, offset, payment_provider, privacy_url, search, sort_by, sort_order, store_name, support_email, support_phone, tagline, terms_url) List StorefrontSettings records with optional filters

## TeamHarness
- `TeamHarness.create`(branch, company_id, note, repo_url, user_id) Create a new TeamHarness record
- `TeamHarness.get`(id) Get a single TeamHarness record by ID
- `TeamHarness.get_mine`() Read your team's harness link (GitHub repository, branch, note). Returns harness: null when none is set yet.
- `TeamHarness.list`(branch, company_id, limit, note, offset, repo_url, search, sort_by, sort_order, user_id) List TeamHarness records with optional filters
- `TeamHarness.set_mine`(branch, note, repo_url) Create or replace your team's harness link. repo_url must be https://github.com/<owner>/<repo> (no /tree/..., query or token); put the branch in `branch`. Empty branch/note clears them.
- `TeamHarness.update`(branch, company_id, id, note, repo_url, user_id) Update an existing TeamHarness record

## UserCompany
- `UserCompany.get`(id) Get a single UserCompany record by ID
- `UserCompany.list`(company_id, joined_at, limit, offset, search, sort_by, sort_order, user_id) List UserCompany records with optional filters

## UserPreference
- `UserPreference.create`(key, user_id, value) Create a new UserPreference record
- `UserPreference.delete`(id) Delete a UserPreference record by ID
- `UserPreference.get`(id) Get a single UserPreference record by ID
- `UserPreference.list`(key, limit, offset, search, sort_by, sort_order, user_id, value) List UserPreference records with optional filters
- `UserPreference.update`(id, key, user_id, value) Update an existing UserPreference record

## WebOrder
- `WebOrder.cancel.confirmed.cancelled`(id) Transition WebOrder from 'confirmed' to 'cancelled'
- `WebOrder.cancel.pending_payment.cancelled`(id) Transition WebOrder from 'pending_payment' to 'cancelled'
- `WebOrder.confirm_payment`(id) Transition WebOrder from 'pending_payment' to 'confirmed'
- `WebOrder.create`(access_token, company_id, coupon_code, coupon_discount, customer_email, customer_name, customer_phone, invoice_id, items, notes, order_date, party_id, payment_failure_reason, payment_gateway_order_id, payment_gateway_payment_id, payment_gateway_signature, payment_method, payment_provider, sales_order_id, shipping_address, shipping_charge, shipping_city, shipping_method_id, shipping_pincode, shipping_state, status, tax_amount, tracking_number, tracking_url) Create a new WebOrder record
- `WebOrder.get`(id) Get a single WebOrder record by ID
- `WebOrder.list`(access_token, company_id, coupon_code, coupon_discount, customer_email, customer_name, customer_phone, grand_total, invoice_id, limit, notes, offset, order_date, party_id, payment_failure_reason, payment_gateway_order_id, payment_gateway_payment_id, payment_gateway_signature, payment_method, payment_provider, sales_order_id, search, shipping_address, shipping_charge, shipping_city, shipping_method_id, shipping_pincode, shipping_state, sort_by, sort_order, status, subtotal, tax_amount, tracking_number, tracking_url) List WebOrder records with optional filters
- `WebOrder.mark_delivered`(id) Transition WebOrder from 'shipped' to 'delivered'
- `WebOrder.process`(id) Transition WebOrder from 'confirmed' to 'processing'
- `WebOrder.ship`(id) Transition WebOrder from 'processing' to 'shipped'
- `WebOrder.update`(access_token, company_id, coupon_code, coupon_discount, customer_email, customer_name, customer_phone, id, invoice_id, items, notes, order_date, party_id, payment_failure_reason, payment_gateway_order_id, payment_gateway_payment_id, payment_gateway_signature, payment_method, payment_provider, sales_order_id, shipping_address, shipping_charge, shipping_city, shipping_method_id, shipping_pincode, shipping_state, tax_amount, tracking_number, tracking_url) Update an existing WebOrder record

## endpoint
- `endpoint.accounting.supplier_scorecard`(party_id) Score one supplier (party_id) or every supplier on on-time delivery, quality and price drift, with each source reported incomplete rather than zeroed when not permitted. Read-only.
- `endpoint.agent.skill.export`(persona_id, persona_name, skill_id) POST /api/agent/skill/export
- `endpoint.agent.tasks.run`(task_id) Launch one of your own scheduled agent tasks now (body: task_id). Owner-only; a task owned by another user is refused.
- `endpoint.agent_governance.escalations`(escalation_id, offset, view) GET /api/agent-governance/escalations
- `endpoint.agent_governance.escalations.assignees`(offset, q, search) GET /api/agent-governance/escalations/assignees
- `endpoint.agent_governance.escalations.raise`(assignee_party_id, reason, reason_code, session_id, sla_minutes) POST /api/agent-governance/escalations/raise
- `endpoint.agent_governance.escalations.update`(action, escalation_id, expect_status, note, outcome) POST /api/agent-governance/escalations/update
- `endpoint.agent_governance.privacy`(offset, privacy_class, session_id) GET /api/agent-governance/privacy
- `endpoint.agent_governance.privacy.forget.preview`(session_id) POST /api/agent-governance/privacy/forget/preview
- `endpoint.agent_governance.skill_sandbox`(candidate_markdown, candidate_policy_id, candidate_skill_id, persona_id, persona_offset, policy_offset, skill_offset) POST /api/agent-governance/skill-sandbox
- `endpoint.approvals.process_decision`(comments, decision, level, request_id) Process an approve/reject decision for an approval step
- `endpoint.calendar.birthdays`(end, start) GET /api/calendar/birthdays
- `endpoint.crm.account_plans`() GET /api/crm/account-plans
- `endpoint.crm.account_plans.create`(account_party_id, buyer_roles, deal_id, milestones, name, operation_key) POST /api/crm/account-plans/create
- `endpoint.crm.account_plans.rename`(account_plan_id, expected_updated_at, name) POST /api/crm/account-plans/rename
- `endpoint.crm.account_plans.task_status`(account_plan_id, expected_status, target_state, task_id) POST /api/crm/account-plans/task-status
- `endpoint.crm.call_note_sources`() GET /api/crm/call-note-sources
- `endpoint.crm.call_notes`() GET /api/crm/call-notes
- `endpoint.crm.call_notes.approve`(approval_key, approval_version, draft_id, edited_content) POST /api/crm/call-notes/approve
- `endpoint.crm.call_notes.draft`(activity_id, operation_key) POST /api/crm/call-notes/draft
- `endpoint.crm.campaign_audiences`() GET /api/crm/campaign-audiences
- `endpoint.crm.campaign_audiences.preview`(audience_id) POST /api/crm/campaign-audiences/preview
- `endpoint.crm.campaign_audiences.sync`(audience_id) POST /api/crm/campaign-audiences/sync
- `endpoint.email.public.subscriber_lists`(list_id) GET /api/email/public/subscriber-lists
- `endpoint.email.rfq.create_quote`(attachments, items, message_id, party_id) Create a draft quotation and design records from selected clean attachments on a tenant-owned RFQ email. This endpoint never sends the message or a quotation.
- `endpoint.inventory.shipping_board`() Dispatch planning board: open SalesOrder lines due to ship by promised date and customer, with ordered/delivered/remaining quantities and their DeliveryChallans. Read-only.
- `endpoint.job_ledger.forensics`(limit, offset, status) GET /api/job-ledger/forensics
- `endpoint.job_ledger.replay`(job_id) POST /api/job-ledger/replay
- `endpoint.job_ledger.retention.preview`(job_id, policy_id) POST /api/job-ledger/retention/preview
- `endpoint.job_ledger.verify`(job_id) POST /api/job-ledger/verify
- `endpoint.make.orders`(late, limit, offset, owner, stage) Orders: one row per open Sales Order line — customer, item, quantity, promised and projected dates, stage, top blocker and owner. Paged: total, has_more and next_offset say when rows remain (limit up to 500). Read-only; requires SalesOrder read.
- `endpoint.make.thread`(entity, id) Read the caller-scoped order thread for a SalesOrder, including linked manufacturing, inspection, shipping and invoice records plus expected missing nodes. Unreadable linked entities are redacted. Read-only; requires SalesOrder read.
- `endpoint.manufacturing.demand_forecast`(history_months, horizon_months) Demand forecast: per item, the monthly average of real sales-order history plus committed open-order demand, for the next horizon months. Read-only.
- `endpoint.manufacturing.job_margin`(sales_order_id) C-105 — read-only SalesOrder-line revenue and manufacturing cost projection joined by stable line key.
- `endpoint.manufacturing.label`(kind, record_id) Label: a printable item or job label whose scannable QR encodes the item code (resolved by the scan catalogue) or the Floor deep link, generated locally.
- `endpoint.manufacturing.purchase_price_variance`(from_date, to_date) C-107 — compare paid/open PO bills with the frozen standard in force on receipt date.
- `endpoint.manufacturing.standard_cost_rolls.drafts`() C-107 — read proposed standard-cost snapshots for roles authorized to freeze them.
- `endpoint.manufacturing.standard_cost_rolls.frozen`() C-107 — read frozen standard-cost snapshots; drafts are never returned.
- `endpoint.mission_control.incident_timeline`(correlation_id) GET /api/mission-control/incident-timeline
- `endpoint.mission_control.incidents`(include_healthy, limit, observation_days, offset) GET /api/mission-control/incidents
- `endpoint.mission_control.runbooks`(limit, offset, status) GET /api/mission-control/runbooks
- `endpoint.mission_control.staffing_forecast`(added_workers, global_concurrency, horizon_hours, observation_days, per_persona_concurrency) POST /api/mission-control/staffing-forecast
- `endpoint.people_directory`() N146. A names-only people directory any member may read: employee id, name and department, and NOTHING else (no salary, bank, statutory id, address or date of birth). The Task/assignee picker and the MCP tool read it instead of the HR-only Employee list.
- `endpoint.public.collective.book`(guest_email, guest_name, guest_phone, guest_timezone, idempotency_key, slug, start_time) POST /api/public/collective/book
- `endpoint.public.collective.claim`(claim_token, guest_email, guest_name, guest_timezone, idempotency_key, offer_id) POST /api/public/collective/claim
- `endpoint.public.collective.meta`(days, slug) GET /api/public/collective/meta
- `endpoint.public.collective.waitlist`(earliest_start, guest_email, guest_name, guest_timezone, idempotency_key, latest_start, note, slug) POST /api/public/collective/waitlist
- `endpoint.storefront.account.orders`(account_key, limit, offset) GET /api/storefront/account/orders
- `endpoint.storefront.categories`() GET /api/storefront/categories
- `endpoint.storefront.checkout`(coupon_code, customer_email, customer_name, customer_phone, items, notes, payment_method, shipping_address, shipping_city, shipping_method_id, shipping_pincode, shipping_state, source_section_key, source_webpage_id) POST /api/storefront/checkout
- `endpoint.storefront.locale`() GET /api/storefront/locale
- `endpoint.storefront.notify_me`(consent, email, item_id, variant_sku) POST /api/storefront/notify-me
- `endpoint.storefront.order`(order_id, order_token) GET /api/storefront/order
- `endpoint.storefront.order.claim`(email, order_id, order_number, order_token) POST /api/storefront/order/claim
- `endpoint.storefront.payment.verify`(order_id, order_token, outcome) POST /api/storefront/payment/verify
- `endpoint.storefront.products`(category, category_id, code, featured, id, ids, limit, offset, search, slug) GET /api/storefront/products
- `endpoint.storefront.shipping_methods`() GET /api/storefront/shipping-methods
- `endpoint.storefront.stock_alerts.queue`(limit, offset, status) POST /api/storefront/stock-alerts/queue
- `endpoint.storefront.stock_alerts.run`(alert_id, limit) POST /api/storefront/stock-alerts/run

## events
- `events.catalog`() List the manufacturing and inventory events you can automate on: name, what it means, its payload fields and how to listen (an Automation with trigger_event on_event). Read-only.

## tools
- `tools.describe`(names) Return the full input schema (and description) for tool names you already know, so you can call them without fetching the whole catalogue. Names outside your scope are reported as not available.
- `tools.preview`(arguments, name) Preview a transition or document-chain tool before calling it: returns the records it would create, the stock/GL it would post, blockers with codes, and its risk class. Nothing is written. Pass the tool name and the arguments you would call it with; the same works by adding preview: true to the call itself.
- `tools.search`(limit, module, query, risk) Search the tools available to you for a business object or verb, e.g. 'purchase order', 'WO complete', 'stock availability'. Returns the matching tool names with a one-line description, ranked. Use tools.describe for the input schema before calling.
