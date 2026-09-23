py/**
 * 利用者ごとにコピーして使うGmail → Googleスプレッドシート連携コードです。
 *
 * 1. SPREADSHEET_ID と SHEET_NAME を自分の値へ変更
 * 2. syncJobHuntingMails を手動実行して権限を許可
 * 3. createHourlyTrigger を1回だけ実行
 */
const SPREADSHEET_ID = 'ここにスプレッドシートID';
const SHEET_NAME = '就活管理';

// 必要に応じて検索条件を変更できます。
const GMAIL_QUERY =
  'newer_than:30d (就活 OR 選考 OR 面接 OR 説明会 OR エントリー OR ES OR 適性検査)';

function syncJobHuntingMails() {
  const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(SHEET_NAME);
  }

  const headers = [
    '受信日時',
    '企業名',
    '件名',
    '概要',
    '状態',
    'メッセージID',
    'Gmail URL',
  ];

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(headers);
  }

  const existingIds = new Set();
  if (sheet.getLastRow() > 1) {
    sheet
      .getRange(2, 6, sheet.getLastRow() - 1, 1)
      .getValues()
      .flat()
      .filter(String)
      .forEach(id => existingIds.add(String(id)));
  }

  const rows = [];
  GmailApp.search(GMAIL_QUERY, 0, 100).forEach(thread => {
    thread.getMessages().forEach(message => {
      const messageId = String(message.getId());
      if (existingIds.has(messageId)) return;

      const subject = message.getSubject() || '';
      const sender = message.getFrom() || '';
      const company = inferCompanyName(subject, sender);
      const snippet = message.getPlainBody().replace(/\s+/g, ' ').slice(0, 300);
      const gmailUrl = `https://mail.google.com/mail/u/0/#all/${thread.getId()}`;

      rows.push([
        message.getDate(),
        company,
        subject,
        snippet,
        message.isUnread() ? '未読' : '既読',
        messageId,
        gmailUrl,
      ]);
    });
  });

  rows.sort((a, b) => b[0] - a[0]);
  if (rows.length) {
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, headers.length).setValues(rows);
  }
}

function inferCompanyName(subject, sender) {
  const bracket = subject.match(/[【\[]([^】\]]+)[】\]]/);
  if (bracket) return bracket[1].trim();

  const senderName = sender.replace(/<[^>]+>/g, '').replace(/["']/g, '').trim();
  return senderName || '企業名不明';
}

function createHourlyTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'syncJobHuntingMails')
    .forEach(trigger => ScriptApp.deleteTrigger(trigger));

  ScriptApp.newTrigger('syncJobHuntingMails')
    .timeBased()
    .everyHours(1)
    .create();
}
