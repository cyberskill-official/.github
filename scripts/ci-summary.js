module.exports = async ({ github, context, core, needs }) => {
  // Guard: ci-summary only makes sense in a pull_request context
  if (!context.issue || !context.issue.number) {
    core.info('Not a pull request context — skipping CI summary comment.');

    return;
  }

  const VALID_RESULTS = new Set(['success', 'failure', 'cancelled', 'skipped']);
  const icon = (r) => r === 'success' ? '✅' : r === 'skipped' ? '⏩' : '❌';

  /**
   * Sanitize a string for safe inclusion in GitHub Markdown.
   * Strips characters that could be used for Markdown/HTML injection.
   */
  const sanitize = (s) => String(s).replace(/[<>&"'`|[\]\\{}\r\n]/g, '');

  const jobNames = {
    'static-checks': 'Static Checks',
    'validate-actions': 'Action Schema Validation',
    'pin-checker': 'SHA Pinning',
    'breaking-change-guard': 'Breaking Change Guard',
    'dependency-review': 'Dependency Review',
    'secret-scan': 'Secret Scanning',
    'git-auth-cleanup': 'Git Auth Cleanup',
    'python-tests': 'Python Tests & Lint',
    'scorecard': 'OSSF Scorecard'
  };
  const rows = Object.entries(needs)
    .map(([k, v]) => {
      const result = VALID_RESULTS.has(v.result) ? v.result : 'unknown';
      const name = jobNames[k] || sanitize(k);

      return `| ${icon(result)} | ${name} | \`${result}\` |`;
    })
    .join('\n');
  const allPassed = Object.values(needs).every(v => v.result === 'success' || v.result === 'skipped');
  const header = allPassed ? '## ✅ CI Passed' : '## ❌ CI Failed';
  const body = [
    header,
    '',
    '| Status | Job | Result |',
    '| ------ | --- | ------ |',
    rows,
    '',
    `_Run: [${context.runId}](${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId})_`
  ].join('\n');

  // Sentinel marker for idempotent comment detection — avoids false matches
  // on user comments that happen to contain "CI Passed" / "CI Failed".
  const COMMENT_MARKER = '<!-- cyberskill-ci-summary -->';
  const markedBody = `${COMMENT_MARKER}\n${body}`;

  // Find existing bot comment to update (idempotent)
  const { data: comments } = await github.rest.issues.listComments({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: context.issue.number,
    per_page: 100
  });
  const existing = comments.find(c =>
    c.user &&
    c.user.type === 'Bot' &&
    c.user.login === 'github-actions[bot]' &&
    c.body &&
    c.body.includes(COMMENT_MARKER)
  );
  if (existing) {
    await github.rest.issues.updateComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      comment_id: existing.id,
      body: markedBody
    });
  } else {
    await github.rest.issues.createComment({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: context.issue.number,
      body: markedBody
    });
  }
};
