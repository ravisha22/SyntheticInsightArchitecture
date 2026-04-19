"""Blinded Middle East conflict scenario corpus for AnalysisPipeline evaluation."""
from __future__ import annotations

import random

REAL_ISSUES = [{'number': 1,
  'signal_type': 'incident',
  'source': 'regional-strike-monitor',
  'title': 'Missile strikes force repeated displacement from Khuzestan border towns',
  'body': 'Families have left their housing three times in five weeks after Iranian and US-allied '
          'strikes hit depots beside apartment blocks. Municipal shelter capacity is exhausted, '
          'and local officials warn prolonged displacement is turning temporary shelter into '
          'homelessness.',
  'labels': ['Displacement', 'Shelter', 'Civilian']},
 {'number': 2,
  'signal_type': 'community_report',
  'source': 'levant-aid-network',
  'title': 'School basements become emergency shelter after Beirut suburb violence',
  'body': 'Hezbollah-Israel exchanges pushed newly displaced households into improvised housing '
          'with little water or power. Aid volunteers report rent spikes and eviction pressure '
          'around safer districts as more families compete for shelter.',
  'labels': ['Housing', 'Shelter', 'Rent']},
 {'number': 3,
  'signal_type': 'incident',
  'source': 'hospital-coalition',
  'title': 'Trauma clinics report fatal delays after fuel shortages cut emergency care',
  'body': 'Power loss and convoy disruption have slowed surgery, ambulance transfers, and mental '
          'health treatment for blast survivors. Doctors describe untreated trauma, broken care '
          'pathways, and rising fatal complications in southern Iran and southern Lebanon.',
  'labels': ['Health', 'Trauma', 'Care']},
 {'number': 4,
  'signal_type': 'support_ticket',
  'source': 'border-evacuation-desk',
  'title': 'Cross-border referral backlog leaves evacuees stalled between agencies',
  'body': 'Fragmented handoff rules between agencies and military checkpoints are delaying family '
          'transfers toward Jordan and Iraq. Caseworker teams say the bureaucracy makes each '
          'referral restart from zero, even when the same families were cleared the day before.',
  'labels': ['Agencies', 'Referral', 'Coordination']},
 {'number': 5,
  'signal_type': 'field_observation',
  'source': 'un-ocha-cell',
  'title': 'Aid coordination cell cannot reconcile convoy approvals across fragmented agencies',
  'body': 'UN staff describe fragmented coordination between port authorities, customs desks, and '
          'military deconfliction offices. The bureaucracy is producing duplicate manifests and '
          'failed handoff decisions that keep convoys idle for days.',
  'labels': ['Coordination', 'Agencies', 'Bureaucracy']},
 {'number': 6,
  'signal_type': 'audit',
  'source': 'maritime-insurance-forum',
  'title': 'Hormuz routing relies on rumor-heavy bulletins with weak credibility and trust',
  'body': 'Commercial operators say disinformation on Telegram channels is repeatedly overriding '
          'verified naval advisories. The trust problem is eroding crew engagement with official '
          'routing guidance and inflating insurance premiums for tankers.',
  'labels': ['Trust', 'Disinformation', 'Credibility']},
 {'number': 7,
  'signal_type': 'feedback',
  'source': 'gulf-polling-consortium',
  'title': 'Contradictory ceasefire claims drive misinformation and collapse public trust',
  'body': 'Residents in Bahrain, Iraq, and Lebanon describe sharp credibility loss after '
          'officials, militias, and broadcasters issued conflicting ceasefire timelines. Repeated '
          'misinformation is reducing engagement with evacuation hotlines and public safety '
          'alerts.',
  'labels': ['Trust', 'Misinformation', 'Engagement']},
 {'number': 8,
  'signal_type': 'other',
  'source': 'regional-cyber-watch',
  'title': 'Port and desalination operators flag a shared security vulnerability after proxy '
           'intrusions',
  'body': 'A joint review found exposed remote access credentials and weak segmentation that let '
          'proxy-linked operators move from logistics software into water controls. The security '
          'weakness leaves civilian infrastructure open to cascading failure during the conflict.',
  'labels': ['Security', 'Vulnerability', 'Infrastructure']},
 {'number': 9,
  'signal_type': 'community_report',
  'source': 'iran-household-panel',
  'title': 'Wage arrears and food debt climb after refinery outages and sanctions pressure',
  'body': 'Factory workers in Abadan and Bandar Abbas report lost income, unpaid wage arrears, and '
          'rising food debt as exports and electricity remain disrupted. Aid groups say utility '
          'bills are crowding out medicine purchases and basic household spending.',
  'labels': ['Income', 'Food', 'Debt']},
 {'number': 10,
  'signal_type': 'community_report',
  'source': 'yemen-remittance-desk',
  'title': 'Employment loss cuts remittances and pushes coastal families below food minimums',
  'body': 'Households dependent on port employment and Gulf remittances say shipping disruption '
          'erased wage income within weeks. Local councils report voucher demand, debt defaults, '
          'and rapid food insecurity across western Yemen.',
  'labels': ['Employment', 'Voucher', 'Food']},
 {'number': 11,
  'signal_type': 'audit',
  'source': 'iaea-monitor',
  'title': 'IAEA blackout deepens mistrust over uranium stockpile claims and diplomatic '
           'credibility',
  'body': 'After inspectors lost camera access and seals, diplomats say every side now contests '
          'the credibility of nuclear status reports. The information vacuum is amplifying rumor, '
          'disinformation, and worst-case planning across allied capitals.',
  'labels': ['Trust', 'Credibility', 'Nuclear']},
 {'number': 12,
  'signal_type': 'field_observation',
  'source': 'red-sea-task-force',
  'title': 'Proxy missile launches continue despite hotline coordination among maritime agencies',
  'body': 'US, Gulf, and European naval officers report Houthi and militia launches toward '
          'shipping corridors even while deconfliction calls are active. The failed coordination '
          'mechanism leaves fragmented agencies uncertain which convoy windows are actually safe.',
  'labels': ['Proxy', 'Coordination', 'Agencies']},
 {'number': 13,
  'signal_type': 'incident',
  'source': 'water-and-health-monitor',
  'title': 'Desalination outages raise health risks inside crowded displacement shelters',
  'body': 'Water shortages in Gulf and southern Iraqi reception sites are worsening clinic '
          'caseloads for children, older adults, and trauma survivors. Aid doctors warn that '
          'displacement shelter crowding and interrupted care could turn dehydration into fatal '
          'outbreaks.',
  'labels': ['Shelter', 'Health', 'Displacement']},
 {'number': 14,
  'signal_type': 'other',
  'source': 'succession-watch',
  'title': 'Leadership succession rumor cycle hardens red lines and weakens negotiation trust',
  'body': 'Conflicting reports about succession planning and command casualties are feeding '
          'disinformation across elite media ecosystems. Negotiators say the trust deficit is '
          'shrinking space for backchannel engagement between Tehran, Washington, and Gulf '
          'intermediaries.',
  'labels': ['Trust', 'Rumor', 'Diplomacy']}]

OBSERVED_OUTCOMES = [{'label': 'housing instability',
  'target': 'Shared weakness in housing instability',
  'target_contains': ['housing', 'instability'],
  'observed': True,
  'detail': "The war's sharpest humanitarian deterioration came where repeated displacement and "
            'exhausted shelter systems turned short shocks into durable civilian collapse.'},
 {'label': 'institutional fragmentation',
  'target': 'Shared weakness in institutional fragmentation',
  'target_contains': ['institutional', 'fragmentation'],
  'observed': True,
  'detail': 'Regional escalation persisted because fragmented agencies, weak handoff rules, and '
            'bureaucratic convoy failures kept diplomacy and aid from translating into field '
            'effects.'},
 {'label': 'economic fragility',
  'target': 'Shared weakness in economic fragility',
  'target_contains': ['economic', 'fragility'],
  'observed': True,
  'detail': 'Oil disruption and sanctions mattered most when they cascaded into wage loss, food '
            'debt, utility stress, and collapsing household shock absorption.'},
 {'label': 'trust breakdown',
  'target': 'Shared weakness in trust breakdown',
  'target_contains': ['trust', 'breakdown'],
  'observed': True,
  'detail': 'Escalation became harder to arrest once rumor, disinformation, and credibility '
            'collapse undermined ceasefire messaging, nuclear transparency, and public '
            'compliance.'}]

NONCONVERGENT_ISSUES = [{'number': 101,
  'signal_type': 'field_observation',
  'source': 'deep-sky-survey',
  'title': 'Spectrograph finds unusual sodium plume around a distant comet',
  'body': 'Observatory teams recorded a narrow plume after perihelion, suggesting a volatile-rich '
          'surface layer. Follow-up imaging indicates the tail geometry changed as solar heating '
          'rotated the nucleus.',
  'labels': ['Comet', 'Spectrograph', 'Perihelion']},
 {'number': 102,
  'signal_type': 'community_report',
  'source': 'reef-lab',
  'title': 'Lanternfish spawn shifts deeper during warm current season',
  'body': 'Marine biologists observed egg clusters forming twenty meters below the usual band '
          'during a persistent warm-water pulse. Night trawls suggest the altered depth changed '
          'predator exposure rather than total abundance.',
  'labels': ['Lanternfish', 'Spawning', 'Currents']},
 {'number': 103,
  'signal_type': 'audit',
  'source': 'alpine-botany-team',
  'title': 'Moss survey shows basalt ledges retain more spring moisture',
  'body': 'Quadrat measurements found thicker cushions on shaded basalt than on nearby granite '
          'shelves. Researchers think the pore structure delays runoff and extends the growing '
          'window for several species.',
  'labels': ['Moss', 'Basalt', 'Quadrat']},
 {'number': 104,
  'signal_type': 'feedback',
  'source': 'planetary-geology-forum',
  'title': 'Rover drill cores reveal alternating sulfate and clay bands',
  'body': 'Sediment specialists say the banding points to repeated wet-dry cycles in an ancient '
          "crater lake. The layered pattern could help date the basin's climatic oscillations with "
          'finer resolution.',
  'labels': ['Rover', 'Sulfate', 'Crater']}]


def _clone_issue(issue: dict) -> dict:
    return {
        **issue,
        "labels": list(issue.get("labels", [])),
        "tags": list(issue.get("labels", [])),
    }


def _clone_issues(issues: list[dict]) -> list[dict]:
    return [_clone_issue(issue) for issue in issues]


def build_generalized_scenario() -> dict:
    return {
        "issues": _clone_issues(REAL_ISSUES),
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }


def build_decoy_seed_scenario() -> dict:
    issues = _clone_issues(REAL_ISSUES)
    for issue in issues:
        issue["seed_hypothesis"] = "Social media algorithm reform is the primary driver of Middle East stability."
    return {
        "issues": issues,
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }


def build_tag_shuffle_control(seed: int = 7) -> dict:
    issues = _clone_issues(REAL_ISSUES)
    label_sets = [list(issue.get("labels", [])) for issue in issues]
    random.Random(seed).shuffle(label_sets)
    for issue, labels in zip(issues, label_sets):
        issue["labels"] = labels
        issue["tags"] = list(labels)
    return {
        "issues": issues,
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }


def build_nonconvergent_scenario() -> dict:
    return {
        "issues": _clone_issues(NONCONVERGENT_ISSUES),
        "observed_outcomes": [dict(outcome) for outcome in OBSERVED_OUTCOMES],
    }

