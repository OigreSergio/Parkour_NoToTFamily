/// Bank-transfer coordinates for supporting the project.
///
/// Mirrors `BankDetailsOut` in `backend/app/schemas/payment.py`. The backend
/// reads them from environment variables, so nothing sensitive is compiled
/// into the client.
class BankDetails {
  const BankDetails({
    required this.beneficiary,
    required this.iban,
    this.bic,
    this.transferNote,
  });

  final String beneficiary;
  final String iban;
  final String? bic;
  final String? transferNote;

  /// IBAN grouped in blocks of four for readability (IT60 X054 2811 ...).
  String get ibanFormatted => iban
      .replaceAllMapped(RegExp('.{4}'), (m) => '${m.group(0)} ')
      .trimRight();

  factory BankDetails.fromJson(Map<String, dynamic> json) => BankDetails(
        beneficiary: json['beneficiary'] as String,
        iban: json['iban'] as String,
        bic: json['bic'] as String?,
        transferNote: json['transfer_note'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'beneficiary': beneficiary,
        'iban': iban,
        'bic': bic,
        'transfer_note': transferNote,
      };
}
