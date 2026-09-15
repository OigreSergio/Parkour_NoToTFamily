/// A risk notice, as served by `GET /api/v1/legal/documents`.
///
/// The text lives on the server and is versioned there: bumping a version puts
/// the notice back in front of everyone without shipping a new build. Nothing
/// in this class hardcodes the wording — see `docs/LEGALE.md`.
class RiskNotice {
  const RiskNotice({
    required this.id,
    required this.version,
    required this.title,
    required this.summary,
    required this.bullets,
    required this.body,
    required this.trigger,
    required this.blocking,
    required this.acceptLabel,
    required this.declineLabel,
  });

  final String id;
  final int version;
  final String title;
  final String summary;

  /// The short points the dialog shows without scrolling.
  final List<String> bullets;

  /// The binding text, behind "Leggi il testo completo".
  final String body;

  /// When the client has to show it: `signup`, `spot_open`, `tutorial_open`,
  /// `signup_minor`.
  final String trigger;

  /// True when the flow must stop until the user chooses.
  final bool blocking;

  final String acceptLabel;
  final String declineLabel;

  factory RiskNotice.fromJson(Map<String, dynamic> json) => RiskNotice(
        id: json['id'] as String,
        version: json['version'] as int,
        title: json['title'] as String,
        summary: json['summary'] as String? ?? '',
        bullets: (json['bullets'] as List<dynamic>? ?? const [])
            .map((b) => b as String)
            .toList(growable: false),
        body: json['body'] as String? ?? '',
        trigger: json['trigger'] as String? ?? 'signup',
        blocking: json['blocking'] as bool? ?? true,
        acceptLabel: json['accept_label'] as String? ?? 'Ho letto e accetto',
        declineLabel: json['decline_label'] as String? ?? 'Non accetto',
      );

  /// Shown when the notices cannot be loaded.
  ///
  /// It says only the sentence that matters, so it cannot drift away from the
  /// real text. A risk warning that fails silently is not a warning, so an
  /// unreachable backend must not mean an unblocked spot.
  static const offline = RiskNotice(
    id: 'liability_offline',
    version: 0,
    title: 'Prima di allenarti',
    summary: 'Non riusciamo a caricare l’informativa completa. '
        'Il punto, però, è questo.',
    bullets: [
      'Il parkour comporta un rischio reale e non eliminabile di infortunio, '
          'anche grave.',
      'La responsabilità di un infortunio in uno spot segnalato qui, o mentre '
          'segui un tutorial pubblicato qui, è esclusivamente tua.',
      'Gli spot sono luoghi di terzi: non li gestiamo, non li controlliamo e '
          'non garantiamo che siano sicuri.',
      'La piattaforma si impegna solo a rendere disponibili le informazioni in '
          'modo gratuito e facilmente accessibile.',
    ],
    body: '',
    trigger: 'spot_open',
    blocking: true,
    acceptLabel: 'Ho capito, procedo sotto la mia responsabilità',
    declineLabel: 'Torna indietro',
  );
}
