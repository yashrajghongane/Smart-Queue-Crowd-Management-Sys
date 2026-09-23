# Smart Queue & Crowd Management System
## Workflow & Behavior Document

## 1. Product Behavior at a Glance

The system has **two separate operating domains**:

```text
                 SMART QUEUE SYSTEM

        ┌─────────────────────┐
        │   DIGITAL QUEUE     │
        │                     │
        │ Patient → Visit     │
        │ → Token             │
        │                     │
        │ WAITING             │
        │ SERVING             │
        │ COMPLETED           │
        │ HOLD / SKIPPED      │
        └──────────┬──────────┘
                   │
                   │ Dashboard
                   │
        ┌──────────┴──────────┐
        │ PHYSICAL SENSING    │
        │                     │
        │ IR Sensor A + B     │
        │        ↓             │
        │ ENTRY / EXIT        │
        │        ↓             │
        │ Occupancy           │
        │        ↓             │
        │ NORMAL / MODERATE   │
        │ HIGH / CRITICAL     │
        └─────────────────────┘
```

The two numbers are **never treated as the same thing**.

For example:

> 8 tokens waiting does not mean 8 people are physically present.

The queue represents **registered service demand**.  
The occupancy system represents **physical movement/people in the monitored area**.

The sensor system never changes a patient's token state.

---

# 2. Actors

| Actor | Main responsibility |
|---|---|
| Patient with phone | Registers, receives token, waits, follows token/status |
| Patient without phone | Gives information to reception staff, who registers them through the same system |
| Reception staff | Handles registration, queue initiation, and basic patient-flow actions |
| Department staff / doctor | Calls tokens, manages serving patients, handles HOLD/RECALL/SKIP/COMPLETE |
| Physical sensor device | Observes doorway movement and produces ENTRY/EXIT events |
| System | Maintains queue state, occupancy count, and capacity alert |

---

# 3. Patient With Phone: Complete Workflow

## Step 1: Registration

The patient scans the hospital/clinic QR or opens the web registration interface.

They provide the required registration information.

```text
Patient
   ↓
QR / Web
   ↓
Registration
```

## Step 2: Visit Creation

The registration is associated with the required department/service.

The system creates a **Visit** for that patient.

```text
Patient
   ↓
Visit
```

## Step 3: Token Creation

The Visit receives a token.

```text
Visit
   ↓
Token
   ↓
WAITING
```

The patient can now wait for service.

## Step 4: Waiting

The patient remains in the queue until staff call the token.

The patient may use the system to see basic queue/status information.

## Step 5: Called

Reception/department staff select the next eligible token.

The token moves:

```text
WAITING → SERVING
```

The patient proceeds for consultation/service.

## Step 6: Completion

After the consultation/service is finished:

```text
SERVING → COMPLETED
```

The token leaves the active queue.

---

# 4. Patient Without Phone: Complete Workflow

A patient without a phone follows the same queue system.

There is **no separate registration system**.

## Step 1

Patient approaches reception.

## Step 2

Reception staff use the same registration interface on their own device.

## Step 3

The same logic is followed:

```text
Staff-assisted registration
          ↓
        Visit
          ↓
        Token
          ↓
       WAITING
```

## Step 4

After that, the patient follows exactly the same queue process as every other patient.

```text
WAITING → SERVING → COMPLETED
```

The important behavior is:

> **Phone or no phone changes only who performs the registration interaction. It does not create a different queue.**

---

# 5. Reception Staff Workflow

Reception staff are mainly responsible for getting patients into the correct queue.

## Normal flow

```text
Patient arrives
      ↓
Registration
      ↓
Check for existing active visit
      ↓
Create Visit
      ↓
Generate Token
      ↓
Token enters WAITING
```

## Reception staff should also be able to

- Register patients using QR/web or staff-assisted registration.
- See the active queue.
- Identify an already-active registration.
- Handle basic queue exceptions according to the system's allowed actions.
- Observe physical occupancy information on the dashboard.

Reception staff do **not** manually change occupancy.

Occupancy comes from the physical device.

---

# 6. Department Staff / Doctor Workflow

Department staff control the actual token lifecycle.

The normal path is:

```text
WAITING
   ↓
CALL NEXT
   ↓
SERVING
   ↓
COMPLETE
   ↓
COMPLETED
```

Exceptions are handled separately.

---

# 7. Token States

## State table

| Token state | Meaning | How it enters the state | What can happen next |
|---|---|---|---|
| **WAITING** | Patient has an active token and is waiting for service | New token created; HOLD released; RECALL returns token | CALL NEXT, HOLD, SKIP |
| **SERVING** | Patient has been called and is currently being handled | CALL NEXT | COMPLETE, HOLD, SKIP, RECALL |
| **HOLD** | Token is temporarily paused and should not normally be called | Staff places token on hold | RECALL to return it to active queue, or SKIP |
| **SKIPPED** | Patient is removed from the active flow without being completed | Staff confirms no-show or patient departure | RECALL to return the token to the queue |
| **COMPLETED** | Service is finished | Staff selects COMPLETE | Terminal state |

### RECALL

**RECALL is an action rather than a permanent token state.**

Its purpose is to bring a temporarily interrupted token back into active handling.

Examples:

```text
HOLD → RECALL → WAITING
```

```text
SKIPPED → RECALL → WAITING
```

If a patient is already being served and simply needs to be called again:

```text
SERVING → RECALL → SERVING
```

There is no need for a separate permanent "RECALL" state.

---

# 8. Normal Token State Flow

```text
                    ┌──────────────┐
                    │   WAITING    │
                    └──────┬───────┘
                           │
                      CALL NEXT
                           ↓
                    ┌──────────────┐
                    │   SERVING    │
                    └──────┬───────┘
                           │
                       COMPLETE
                           ↓
                    ┌──────────────┐
                    │  COMPLETED   │
                    └──────────────┘
```

Exceptions:

```text
WAITING ──HOLD──→ HOLD
  ↑                │
  └──RECALL────────┘

WAITING ──SKIP──→ SKIPPED
  ↑                  │
  └──RECALL──────────┘

SERVING ──HOLD──→ HOLD
SERVING ──SKIP──→ SKIPPED
SERVING ──RECALL→ SERVING
```

---

# 9. Token Edge Cases

## A. Duplicate registration attempt

Example:

A patient already has an active token for the same current visit/queue and attempts registration again.

Expected behavior:

```text
Existing active Visit/Token found
          ↓
Do not create another active token
          ↓
Show the existing token/status
```

The system should prevent two active tokens being created accidentally for the same patient and same current visit.

A genuinely separate future or new visit is treated as a new visit rather than a duplicate.

---

## B. Two staff members press CALL NEXT at the same time

The system must not create two competing "next" patients for the same queue/service position.

Expected behavior:

```text
Two CALL NEXT actions
        ↓
One token is accepted first
        ↓
Token becomes SERVING
        ↓
Second action sees the updated queue
        ↓
It does not create a duplicate serving state
```

The result must remain consistent even when two staff members act almost simultaneously.

---

## C. Patient never shows up

A token can remain in:

```text
WAITING
```

The sensor does not automatically decide that the patient is absent.

If staff determine that the patient has not arrived after the appropriate waiting period:

```text
WAITING → SKIPPED
```

The queue then continues.

If the patient later returns and staff decide to bring the token back:

```text
SKIPPED → RECALL → WAITING
```

---

## D. Patient leaves before being called

If a patient leaves before service:

```text
WAITING → SKIPPED
```

This is a staff decision.

The occupancy sensor may detect that someone exited the waiting area, but it cannot know that the person was that particular token.

Therefore:

> **EXIT event does not automatically SKIP a token.**

---

## E. Patient leaves while being served

If the patient temporarily leaves:

```text
SERVING → HOLD
```

Staff can later use RECALL.

If staff confirm that the patient has left and will not continue:

```text
SERVING → SKIPPED
```

Again, the physical sensor does not make this decision.

---

## F. Patient completes service normally

```text
SERVING → COMPLETE → COMPLETED
```

COMPLETED is the end of the current token lifecycle.

---

# 10. Physical Sensing Workflow

The physical sensing system is independent of the patient-token system.

It consists of:

```text
IR Sensor A
      +
IR Sensor B
      ↓
ESP32
      ↓
Movement interpretation
      ↓
ENTRY / EXIT
      ↓
Occupancy count
      ↓
Capacity alert
```

The device monitors **one defined waiting-area doorway**.

---

# 11. Physical Device Behavior

## Normal ENTRY

A valid sequence:

```text
Sensor A triggered
       ↓
Sensor B triggered
       ↓
ENTRY event
       ↓
Occupancy + 1
```

## Normal EXIT

A valid reverse sequence:

```text
Sensor B triggered
       ↓
Sensor A triggered
       ↓
EXIT event
       ↓
Occupancy - 1
```

The device does not identify who the person is.

It only determines that a valid movement sequence occurred.

---

# 12. Physical Occupancy States

| Physical condition | Device result |
|---|---|
| Valid A → B sequence | ENTRY |
| Valid B → A sequence | EXIT |
| No valid sequence | No occupancy change |
| Ambiguous/incomplete sequence | No trusted occupancy change |
| Occupancy rises/falls | Dashboard number updates |
| Occupancy crosses configured capacity level | Capacity alert changes |

The four alert levels are:

```text
NORMAL
MODERATE
HIGH
CRITICAL
```

The exact numerical thresholds are configuration/tuning work and should be validated during testing.

---

# 13. Physical Sensing Edge Cases

## A. Only one sensor fires

Example:

```text
Sensor A → triggered
Sensor B → never triggered
```

No reliable direction has been established.

Expected behavior:

```text
No ENTRY/EXIT
Occupancy unchanged
```

The event is treated as incomplete/ambiguous rather than blindly counting a person.

---

## B. Person reverses direction

Example:

```text
Person begins crossing
      ↓
First sensor triggered
      ↓
Person turns around
      ↓
Crossing is not completed
```

The device should not count an ENTRY or EXIT unless it sees a valid movement sequence.

If a person fully crosses and then immediately returns:

```text
A → B = ENTRY
B → A = EXIT
```

The occupancy therefore returns to its previous value.

---

## C. Two people cross together

Two people moving very close together can produce overlapping sensor triggers.

With the prototype's two-sensor arrangement, some such movements may be ambiguous.

Expected behavior:

```text
Overlapping/uncertain sequence
          ↓
Cannot confidently determine direction
          ↓
Do not blindly change occupancy
```

This is one of the hardware behaviors that must be measured during testing.

The system should prefer an **uncertain result over confidently reporting a wrong count**.

---

## D. EXIT occurs when occupancy is already zero

Occupancy should never become negative.

Therefore:

```text
Occupancy = 0
      +
EXIT
      ↓
Occupancy remains 0
```

The event can be treated as an abnormal condition for later investigation.

---

## E. Device restart / power interruption

After a restart, the device cannot automatically assume that the physical area is empty.

The operational procedure must therefore include an initialization/reset condition where the actual waiting-area occupancy is known or confirmed before relying on the count.

This is a product reliability issue to validate during testing.

---

# 14. Queue State and Occupancy State on the Dashboard

The dashboard should visually separate the two systems.

For example:

```text
┌─────────────────────────────────────────┐
│ GENERAL OPD                             │
│                                         │
│ DIGITAL QUEUE                           │
│                                         │
│ Waiting:          7                     │
│ Serving:          Token 102             │
│                                         │
├─────────────────────────────────────────┤
│ PHYSICAL WAITING AREA                   │
│                                         │
│ Occupancy:        8 people              │
│ Capacity:         HIGH                  │
│                                         │
└─────────────────────────────────────────┘
```

The dashboard should make it obvious that:

**Waiting = registered queue demand**

while:

**Occupancy = physically detected people in the monitored area**

Neither number automatically changes the other's state.

---

# 15. How Staff Interpret Both Numbers

The value comes from seeing the two measurements together.

### Example 1

```text
Waiting:    12
Occupancy:   5
```

There is substantial registered demand, but relatively few people are physically present in the monitored area.

### Example 2

```text
Waiting:     4
Occupancy:  15
```

There are relatively few active queue tokens, but the monitored area is physically crowded.

The system therefore gives staff **two different operational signals**, rather than pretending one number explains everything.

---

# 16. Worked 10-Minute Scenario

For illustration only, assume this waiting area has a configured physical capacity of **10 people** and the alert bands are temporarily defined as:

```text
0–5   = NORMAL
6–7   = MODERATE
8–9   = HIGH
10    = CRITICAL
```

These values are examples for demonstrating the behavior. Final thresholds are a testing decision.

### Starting situation: 10:00

```text
Waiting:   6
Serving:   Token 100
Occupancy: 5
Alert:     NORMAL
```

---

### 10:01

Two patients register.

```text
Waiting:   8
Serving:   Token 100
Occupancy: 5
Alert:     NORMAL
```

Queue increased because of new registrations.

Occupancy did not change because the physical sensor did not detect an ENTRY.

---

### 10:02

One person enters the waiting area.

```text
ENTRY
   ↓
Occupancy: 6
```

Dashboard:

```text
Waiting:   8
Serving:   Token 100
Occupancy: 6
Alert:     MODERATE
```

Notice that the queue remained at 8.

---

### 10:03

Doctor/staff completes Token 100 and calls Token 101.

```text
Token 100:
SERVING → COMPLETED

Token 101:
WAITING → SERVING
```

Dashboard:

```text
Waiting:   7
Serving:   Token 101
Occupancy: 6
Alert:     MODERATE
```

Again, occupancy was not changed by the token transition.

---

### 10:04

Two people enter the waiting area.

```text
ENTRY
ENTRY

Occupancy: 6 → 8
```

Dashboard:

```text
Waiting:   7
Serving:   Token 101
Occupancy: 8
Alert:     HIGH
```

---

### 10:05

Another patient registers.

```text
Waiting:   8
Serving:   Token 101
Occupancy: 8
Alert:     HIGH
```

The queue increases, while physical occupancy remains unchanged.

---

### 10:06

One person leaves the waiting area.

```text
EXIT
   ↓
Occupancy: 8 → 7
```

Dashboard:

```text
Waiting:   8
Serving:   Token 101
Occupancy: 7
Alert:     MODERATE
```

---

### 10:07

Token 101 is completed.

Token 102 is called.

```text
Token 101:
SERVING → COMPLETED

Token 102:
WAITING → SERVING
```

Dashboard:

```text
Waiting:   7
Serving:   Token 102
Occupancy: 7
Alert:     MODERATE
```

---

### 10:08

Token 103 has not arrived.

Staff determine that the patient is not going to appear and skip the token.

```text
Token 103:
WAITING → SKIPPED
```

Dashboard:

```text
Waiting:   6
Serving:   Token 102
Occupancy: 7
Alert:     MODERATE
```

The sensor does not participate in this decision.

---

### 10:09

Two people leave the waiting area.

```text
EXIT
EXIT

Occupancy: 7 → 5
```

Dashboard:

```text
Waiting:   6
Serving:   Token 102
Occupancy: 5
Alert:     NORMAL
```

---

### 10:10

Token 102 is completed and Token 104 is called.

```text
Token 102:
SERVING → COMPLETED

Token 104:
WAITING → SERVING
```

Dashboard:

```text
Waiting:   5
Serving:   Token 104
Occupancy: 5
Alert:     NORMAL
```

---

# 17. What This Scenario Demonstrates

During ten minutes:

```text
DIGITAL QUEUE

6 → 8 → 7 → 8 → 7 → 6 → 5
```

while:

```text
PHYSICAL OCCUPANCY

5 → 6 → 6 → 8 → 8 → 7 → 7 → 5 → 5
```

The two values move independently.

That is the central behavior of the product.

A registration changes the digital queue.

A staff action changes a token state.

A sensor event changes physical occupancy.

A capacity alert is derived from physical occupancy.

These are connected through the dashboard, but **one system does not falsely control the other**.

---

# 18. Core Rules of the Whole Product

The team should treat these as the fundamental behavior rules:

### Rule 1
**Every service interaction begins with a Patient → Visit → Token relationship.**

### Rule 2
**QR/web registration and staff-assisted registration end in exactly the same queue flow.**

### Rule 3
**Only staff actions change token state.**

### Rule 4
**Sensors never call, skip, hold, complete, or otherwise identify a patient's token.**

### Rule 5
**Physical occupancy and digital queue count are always displayed separately.**

### Rule 6
**A sensor only produces trusted ENTRY/EXIT events when movement can be classified confidently.**

### Rule 7
**Ambiguous sensor behavior should not automatically produce a trusted occupancy change.**

### Rule 8
**COMPLETED is the normal terminal token state.**

### Rule 9
**SKIPPED means the token was intentionally removed from the active flow, not that the patient was successfully served.**

### Rule 10
**RECALL is an action used to bring an interrupted/skipped token back into active handling.**

---

# 19. Overall Product Behavior

The entire system can therefore be summarized as:

```text
                     PATIENT
                        │
           ┌────────────┴────────────┐
           │                         │
       Has phone                 No phone
           │                         │
       QR / Web                 Reception staff
           │                         │
           └────────────┬────────────┘
                        ↓
                  REGISTRATION
                        ↓
                      VISIT
                        ↓
                     TOKEN
                        ↓
                    WAITING
                        ↓
                    CALL NEXT
                        ↓
                    SERVING
                  ↙     ↓      ↘
               HOLD   COMPLETE  SKIP
                │        ↓       │
              RECALL  COMPLETED RECALL
                │                │
                └────→ WAITING ←─┘


                  SEPARATE SYSTEM
                        │
              IR SENSOR A + B
                        ↓
                Movement detected
                        ↓
                 ENTRY / EXIT
                        ↓
                  OCCUPANCY
                        ↓
            NORMAL / MODERATE / HIGH /
                    CRITICAL
                        │
                        ↓
                   DASHBOARD
```

## Final product principle

**The digital system answers:**

> “Who is waiting for service, and what is the state of their token?”

**The physical system answers:**

> “What is happening physically in the monitored waiting area?”

**The dashboard brings those two views together without pretending they are the same measurement.**