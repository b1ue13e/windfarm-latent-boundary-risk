# v14 figure brief

Use five figures to explain a fixed forecast-to-reserve workflow and its observed trade-offs. All graphics are original vector drawings; downloaded TSTE/gallery images are design references only.

1. Architecture and timing: separate the forecast data cutoff, reserve decision and target; show current telemetry, frozen learner, two nonnegative clips, historical offset and future-only scoring.
2. Worked day: all 144 recorded requests, raw estimates and subsequent shortfalls; all five historical offsets. No cherry-picked event or uncertainty band.
3. Matched updates: all four arms, two estimators and five fits; stored simultaneous intervals; all 35 shared weather days.
4. Cross-year trade-off: five versus112 reserve inputs, stored cost and event criteria, procurement/shortfall accounting and all20 fit endpoints.
5. Temporal consistency: complete365/120-day calendars plus daily operating-cost context;12 days with no eligible targets remain visibly missing.

Learning from references: Gilbert2020 Fig1 separates operational inputs from fitting/evaluation; Soares2016 links policy choices to economic outcomes; Wen2022 uses complementary calibration and temporal views. Gallery PatchTST uses a monotone main flow with detailed internals separated. We reuse these compositional principles, not images, methods or claims.

Production: 7.16-inch IEEE double-column width; Arial7–9pt, PDF with embedded TrueType, editable SVG,600dpiPNG. No new model fits, forecasts, calibration, bootstrap or hypothesis tests. Stored intervals and thresholds are unchanged. Deterministic arithmetic only for plotted paired differences, component accounting and fit averages.
