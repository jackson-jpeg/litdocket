import Link from 'next/link';

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="mb-8">
            <Link href="/" className="text-blue-600 hover:text-blue-700 text-sm">
              &larr; Back to Home
            </Link>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-8">Terms of Service</h1>

          <div className="prose prose-blue max-w-none text-gray-700 space-y-6">
            <p className="text-sm text-gray-500">Last updated: January 2025</p>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">1. Acceptance of Terms</h2>
              <p>
                By accessing or using LitDocket (&quot;the Service&quot;), you agree to be bound by these Terms of Service.
                If you do not agree to these terms, please do not use the Service.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">2. Description of Service</h2>
              <p>
                LitDocket is a legal docketing and case management platform that provides AI-powered deadline
                tracking, document analysis, and case management tools for legal professionals.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">3. User Responsibilities</h2>
              <p>You agree to:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Provide accurate and complete information when creating an account</li>
                <li>Maintain the security of your account credentials</li>
                <li>Use the Service only for lawful purposes</li>
                <li>Not share your account with unauthorized users</li>
                <li>Verify all AI-generated deadline calculations before relying on them</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">4. Disclaimer of Warranties</h2>
              <p>
                THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTY OF ANY KIND. While we strive to provide accurate
                deadline calculations, LitDocket does not guarantee the accuracy of any AI-generated content,
                including but not limited to deadline calculations, document summaries, or legal analysis.
              </p>
              <p className="mt-3">
                <strong>IMPORTANT:</strong> Users are solely responsible for verifying all deadlines and legal
                information. LitDocket is not a substitute for professional legal judgment.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">5. Limitation of Liability</h2>
              <p>
                IN NO EVENT SHALL LITDOCKET BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL,
                OR PUNITIVE DAMAGES, INCLUDING WITHOUT LIMITATION, LOSS OF PROFITS, DATA, OR GOODWILL,
                ARISING FROM YOUR USE OF THE SERVICE.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">6. Intellectual Property</h2>
              <p>
                All content, features, and functionality of the Service are owned by LitDocket and are
                protected by copyright, trademark, and other intellectual property laws.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">7. Termination</h2>
              <p>
                We reserve the right to terminate or suspend your account at any time for any reason,
                including violation of these Terms of Service.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">8. Changes to Terms</h2>
              <p>
                We may modify these Terms at any time. Continued use of the Service after changes
                constitutes acceptance of the modified Terms.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">9. Contact</h2>
              <p>
                For questions about these Terms, please contact us at support@litdocket.com.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
