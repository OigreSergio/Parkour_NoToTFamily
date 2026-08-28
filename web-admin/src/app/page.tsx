import { redirect } from 'next/navigation';

// Le segnalazioni prima degli spot: uno spot in attesa fa aspettare chi l'ha
// proposto, una segnalazione fa aspettare chi ha subito qualcosa.
export default function Home() {
  redirect('/reports');
}
