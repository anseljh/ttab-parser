# TTAB XML DTD Official Structure Analysis

Based on the official USPTO TTAB DTD documentation, here are the key XML elements and structure:

## Root Structure
```xml
<ttab-proceedings>
  <version>
    <version-no>1.0</version-no>
    <version-date>YYYYMMDD</version-date>
  </version>
  <action-key-code>DA|AN</action-key-code>
  <transaction-date>YYYYMMDD</transaction-date>
  
  <proceeding-information>
    <data-available-code>Y|N</data-available-code>
    <proceeding-entry>...</proceeding-entry>
  </proceeding-information>
</ttab-proceedings>
```

## Proceeding Entry Structure
```xml
<proceeding-entry>
  <number>91XXXXXX</number>  <!-- 8-digit: 91=Opposition, 92=Cancellation -->
  <type-code>OPP|CAN|EXA|CNU</type-code>
  <filing-date>YYYYMMDD</filing-date>
  <status-code>1-9|A-P</status-code>
  <status-update-date>YYYYMMDD</status-update-date>
  
  <party-information>
    <party>
      <identifier>12345678</identifier>
      <role-code>P|D</role-code>  <!-- P=Plaintiff, D=Defendant -->
      <name>Party Name</name>
      <orgname>Organization Name</orgname>
      <address-information>...</address-information>
      <attorney-information>...</attorney-information>
    </party>
  </party-information>
  
  <prosecution-history>...</prosecution-history>
</proceeding-entry>
```

## Key Differences from Current Implementation

1. **Root Element**: Should be `<ttab-proceedings>` not custom elements
2. **Proceeding Numbers**: Follow strict format (91=Opposition, 92=Cancellation, etc.)
3. **Party Roles**: Use "P" (Plaintiff) and "D" (Defendant) instead of applicant/opposer
4. **Date Format**: Strict YYYYMMDD format (8-digit numeric)
5. **Status Codes**: Defined numeric/alpha codes (1-9, A-P)
6. **Element Names**: Hyphenated format (e.g., `filing-date`, `party-information`)

## Opinion-Specific Elements
The documentation shows that TTAB proceedings include both administrative filings AND final decisions/opinions. Opinions would be found in the prosecution history section with specific status codes indicating final decisions.