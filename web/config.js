// content_feed front-end configuration. This file is public: never put secret keys here.
window.FEED_CONFIG = {
  // Backend base URL. Empty = demo mode: built-in demo posts, uploads stay on this phone,
  // tips and payouts are simulated.
  apiUrl: "",

  currency: "NGN",
  locale: "en-NG",
  platformFee: 0.2,      // share of each tip the platform keeps; the creator gets the rest
  minPayout: 1000,       // smallest mobile money payout
  maxUploadMB: 50,
  maxVideoSeconds: 60,
  payProviders: ["OPay", "PalmPay", "MTN MoMo", "M-Pesa", "Airtel Money"]
};
