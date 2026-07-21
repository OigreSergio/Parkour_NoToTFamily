import '../models/bank_details.dart';
import '../services/api_client.dart';

/// Reads the project's bank-transfer coordinates from the backend.
class PaymentRepository {
  PaymentRepository(this._api);

  final ApiClient _api;

  static const String _bankDetailsPath = '/api/v1/payments/bank-details';

  /// Fetch the bank-transfer details, or `null` when the deployment has not
  /// configured them yet (backend answers 404 in that case).
  Future<BankDetails?> fetchBankDetails() async {
    try {
      final data = await _api.getJson(_bankDetailsPath);
      return BankDetails.fromJson(data as Map<String, dynamic>);
    } on ApiException catch (e) {
      if (e.statusCode == 404) return null;
      rethrow;
    }
  }
}
