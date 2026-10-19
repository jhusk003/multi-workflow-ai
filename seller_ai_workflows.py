"""AI drafts connected to each specialist's conversation; explicitly saved or applied.

No automatic publication, outbound messages, or permanent storage. Each session's
existing workspaces own their applied drafts and chat messages.
"""
from __future__ import annotations
from datetime import datetime
import io
import json
import uuid
import streamlit as st
from seller_character_brain import reply, BrainUnavailable
from seller_business_engine import parse_inventory

PREFS={
  'Shop name':'', 'Audience':'', 'Brand voice':'Warm, concise and genuine',
  'Product strengths':'', 'Shipping policy':'', 'Returns policy':'',
  'Target platforms':'Etsy / Shopify',
}
KIND_DIRECTIVES={
 'inventory':'Create a prioritised inventory interpretation. Use provided SKU stock/velocity/lead times. Mark assumptions, give actionable next steps. Never call the Wilson EOQ math TabPFN.',
 'listing':'Write one original, ready-to-edit product listing draft for the selected product and target platform, including title, description, keyword/tag ideas and missing details as [VERIFY] placeholders. Do not invent material, sizing, claims or stock. The bulk CSV export is a separate deterministic tool.',
 'marketing':'Generate new distinct marketing concepts based on the requested campaign, audience, brand voice, and platforms. Give campaign angle, sample post/email copy, CTA and alternate idea, not a recurring generic template.',
 'messages':'Write an editable reply to the provided real or test customer message. Follow saved shop shipping/returns policy, do not promise refunds or dispatch without evidence. Offer a tactfully different version when asked to revise.',
 'research':'Help interpret the provided competitor findings or develop a research plan. Do not fabricate live prices or claim web/SerpApi access unless data are supplied.',
 'supplier':'Create a supplier comparison, outreach draft or follow-up plan using only provided supplier notes, estimated PO and current inventory. Unknown quotes and ETAs must be marked [VERIFY].',
 'operations':'Interpret the deterministic draft purchase order and write a packing, scheduling, or supplier communication plan. Do not claim the order was actually sent.',
 'finance':'Interpret the available inventory/financial CSV or estimated P&L; offer scenario planning and potential next actions, with clearly marked assumptions. Never claim tax filing or state nexus certainty.',
}

def get_prefs():
    return {k: str(st.session_state.get('sa_pref_'+str(i),v)) for i,(k,v) in enumerate(PREFS.items())}


def brand_settings():
    st.markdown('### 🎀 Brand & AI generation preferences')
    st.caption('These preferences guide all four AI specialists and their workspace generators in this Streamlit session; they are not published to marketplaces.')
    for i,(label,default) in enumerate(PREFS.items()):
        key='sa_pref_'+str(i)
        if key not in st.session_state:
            st.session_state[key]=default
        if label in ('Product strengths','Shipping policy','Returns policy'):
            st.text_area(label,key=key,height=77)
        elif label=='Brand voice':
            st.text_input(label,key=key,placeholder='e.g. cheerful, clear, not overly salesy')
        else:
            st.text_input(label,key=key)
    st.download_button('Back up my brand preferences (JSON)', json.dumps(get_prefs(),indent=2).encode('utf-8'),
                       file_name='seller_assist_brand_preferences.json',mime='application/json',key='sa_pref_export')
    st.caption('To use these settings again in a new session, keep your backup; this version has no account-wide persistence.')


def inventory_reference(c, data):
    if st.session_state.get('sa_shared_kind')=='inventory' and st.session_state.get('sa_shared_csv'):
        return st.session_state['sa_shared_csv'],'Your uploaded inventory CSV'
    return data.inventory_csv,'Built-in SAMPLE inventory (upload your own under Settings & Data)'


def generate_draft(workflow_id, mode, kind, c, user_request, reference='', prior=''):
    if kind not in KIND_DIRECTIVES:
        raise ValueError('Unknown AI workflow')
    assistant=c['ASSISTANTS'][mode]
    workspace=c['workspaces'][mode]
    prompt=(f"WORKSPACE TASK: {KIND_DIRECTIVES[kind]}\nUser-specific instructions: {user_request.strip()}\n"
            'Return just the usable editable draft, with short headers as helpful.')
    if prior.strip():
        prompt += '\nPREVIOUS UNSAVED DRAFT FOR REVISION:\n' + prior[:10000]
    text, provider=reply(mode,assistant,workspace,prompt,reference,get_prefs(),c['secret'])
    workspace['last_model_used']=provider
    return text,provider


def apply_to_chat(workspace, mode, kind, request, text):
    content=str(text or '').strip()
    if not content:
        raise ValueError('Edit or generate some content first.')
    digest=(mode,kind,request,content)
    if workspace.get('last_applied_draft') == digest:
        return False
    stamp=datetime.now().strftime('%b %d · %I:%M %p')
    workspace.setdefault('messages',[]).extend([
        {'role':'user','content':f'[Applied {kind} workspace draft] {request.strip() or "Please continue working with this draft."}', 'time':stamp},
        {'role':'assistant','content':f'**Editable {kind} draft saved from the workspace:**\n\n{content}\n\nI can refine this draft with you in our conversation.', 'time':stamp},
    ])
    workspace['last_reply']=f'{kind.title()} draft saved to our conversation. I can refine it with you.'
    workspace['reply_id']=uuid.uuid4().hex
    workspace['last_audio']=''
    workspace['last_applied_draft']=digest
    return True


def workflow_panel(workflow_id,mode,kind,c,reference='',label='',default_instruction=''):
    """One shared brain per character. User can edit/regenerate/save/apply output."""
    assistant=c['ASSISTANTS'][mode]
    workspace=c['workspaces'][mode]
    prefix='sa_wf_'+workflow_id
    st.markdown(f'#### {label or kind.title()} · Ask {assistant["name"]}')
    st.caption('AI uses this character’s existing conversation and your saved brand preferences. Clicking Generate sends the shown context to your configured AI provider; it does not contact customers or publish anything.')
    st.session_state.setdefault(prefix+'_request', default_instruction)
    request=st.text_area('What should this version do?',key=prefix+'_request',height=92)
    feedback=st.text_input('Revision feedback (optional)',key=prefix+'_feedback',placeholder='e.g. shorter, friendlier, add an alternative headline')
    previous=st.session_state.get(prefix+'_edited','')
    a,b=st.columns(2)
    with a: generate=st.button('✨ Generate new AI draft',key=prefix+'_generate',use_container_width=True)
    with b: revise=st.button('↻ Regenerate with feedback',key=prefix+'_revise',use_container_width=True,disabled=not bool(previous.strip()))
    if generate or revise:
        if not request.strip():
            st.warning('Describe what you want the specialist to generate.')
        elif revise and not feedback.strip():
            st.warning('Enter feedback to guide the revision.')
        else:
            instructions=request + (('\nRevision requirements: '+feedback) if revise else '')
            try:
                with st.spinner(f'{assistant["name"]} is preparing an original draft…'):
                    result, provider=generate_draft(workflow_id,mode,kind,c,instructions,reference,
                                                     previous if revise else '')
                st.session_state[prefix+'_edited']=result
                st.session_state[prefix+'_provider']=provider
                st.session_state[prefix+'_version']=st.session_state.get(prefix+'_version',0)+1
                st.rerun()
            except BrainUnavailable as error:
                st.error(str(error))
    if st.session_state.get(prefix+'_edited','').strip():
        st.caption('Generated with '+st.session_state.get(prefix+'_provider','configured AI')+'. Edit freely before saving.')
        st.text_area('Edit this draft',key=prefix+'_edited',height=275)
        content=st.session_state[prefix+'_edited']
        c1,c2,c3=st.columns(3)
        with c1:
            if st.button('💾 Save draft',key=prefix+'_save',use_container_width=True):
                if content.strip():
                    saved=workspace.setdefault('artifacts',[])
                    saved.append({'id':uuid.uuid4().hex,'kind':kind,'request':request,'content':content,
                                  'time':datetime.now().isoformat(timespec='seconds')})
                    st.success(f'Saved to {assistant["name"]}’s drafts for this session.')
        with c2:
            if st.button('💬 Apply to character chat',key=prefix+'_apply',use_container_width=True):
                if apply_to_chat(workspace,mode,kind,request,content):
                    st.success(f'Added the edited draft to {assistant["name"]}’s conversation. Continue from AI Team → {assistant["name"]}.')
                else:
                    st.info('This exact version is already in the conversation.')
        with c3:
            st.download_button('⬇️ Download draft',data=content.encode('utf-8'),
                file_name=f'seller_assist_{kind}_draft.md',mime='text/markdown',key=prefix+'_download',use_container_width=True)
    if workspace.get('artifacts'):
        with st.expander(f'{assistant["name"]}’s saved drafts ({len(workspace["artifacts"])})'):
            for artifact in reversed(workspace['artifacts'][-12:]):
                st.markdown(f'**{artifact["kind"].title()} — {artifact["time"]}**')
                st.text_area('Saved text',value=artifact['content'],height=115,disabled=True,key=f'{prefix}_{artifact["id"]}')


def specialist_room_tools(mode, workspace, *, inventory_csv, fee_rate, run_forecast, run_po, run_listing, run_pl):
    """Tools genuinely specific to the selected assistant, not all four on every room."""
    st.markdown('#### Your specialist’s tools')
    if mode.startswith('Level 1:'):
        if st.button('📦 Calculate stock and reorder plan',key='sa_specialist_morgan'):
            workspace['tabpfn_report']=run_forecast(inventory_csv,fee_rate)
        if workspace.get('tabpfn_report'):
            with st.expander('Wilson EOQ stock plan',expanded=True):st.markdown(workspace['tabpfn_report'])
    elif mode.startswith('Level 2:'):
        if st.button('🏷️ Generate bulk listing CSV draft',key='sa_specialist_jordan'):
            workspace['exported_listing_csv']=run_listing(inventory_csv)
        if workspace.get('exported_listing_csv'):
            st.download_button('Download listing CSV draft',workspace['exported_listing_csv'],file_name='listing_draft.csv',key='sa_specialist_listing_download')
    elif mode.startswith('Level 3:'):
        if st.button('🚚 Build itemized draft PO',key='sa_specialist_taylor'):
            workspace['generated_po']=run_po(workspace)
        if workspace.get('generated_po'):
            with st.expander('Draft PO',expanded=True):st.markdown(workspace['generated_po'])
    else:
        if st.button('💰 Calculate estimated product P&L',key='sa_specialist_alex'):
            workspace['schedule_c_pl']=run_pl(inventory_csv,fee_rate)
        if workspace.get('schedule_c_pl'):
            with st.expander('Estimated P&L',expanded=True):st.markdown(workspace['schedule_c_pl'])
    artifacts=workspace.get('artifacts',[])
    if artifacts:
        with st.expander('📂 Drafts saved from workspaces',expanded=False):
            for a in artifacts[-8:][::-1]:
                st.markdown(f'**{a["kind"].title()}** ({a["time"]})')
                st.text(a['content'][:650])
    st.caption('Save an editable draft on its workspace page, then apply it to this assistant’s chat to discuss it together.')
