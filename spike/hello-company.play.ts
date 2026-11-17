import deepline from 'deepline';

// Throwaway spike: one checkpoint, no provider tool, so a real run should cost almost nothing.
export const config = {
  description: 'Echo one domain and the time it was checked.',
  billing: { maxCreditsPerRun: 2 },
};

export default async function (input: { domain: string }) {
  // 0 means a fresh checkpoint. There is no provider result to reuse.
  const echo = await deepline.step(
    'echo',
    () => ({
      domain: input.domain,
      checked_at: new Date().toISOString(),
    }),
    { staleAfterSeconds: 0 },
  );

  return { ok: true, echo };
}
