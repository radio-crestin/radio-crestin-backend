import React from 'react';
import HeadContainer from '@/components/HeadContainer';
import Body from '@/components/Body/Body';
import {Box, Container, Heading} from '@chakra-ui/react';
import Footer from '@/components/Footer/Footer';
import Analytics from '@/components/Analytics/Analytics';
import {seoPrivacyPolicy} from '@/utils/seo';
import {ContactModalLink} from '@/components/ContactModalLink/ContactModalLink';

export default function PrivacyPolicy() {
  return (
    <>
      <HeadContainer seo={seoPrivacyPolicy} />
      <Body>
        <Container maxW={'8xl'}>
          <Box
            display={'flex'}
            alignItems={'center'}
            justifyContent={'flex-end'}
            my={4}
            gap={2}>
            <ContactModalLink />
          </Box>
          <Box flexWrap={'wrap'} className={'privacy_content'}>
            <Heading my={5}>Radio Crestin App Privacy Policy.</Heading>
            <Heading size={'md'} my={5}>
              Last updated: 14.07.2023
            </Heading>

            <p>
              This Privacy Policy describes how <b>Radio Crestin App</b> (the
              &quot;App&quot;, &quot;we&quot;, &quot;us&quot;, or
              &quot;our&quot;) collects, uses, and discloses your personal
              information when you visit, use our services or otherwise
              communicate with us (collectively, the &quot;Services&quot;). For
              purposes of this Privacy Policy, &quot;you&quot; and
              &quot;your&quot; means you as the user of the Services, whether
              you are a customer, website visitor, or another individual whose
              information we have collected pursuant to this Privacy Policy.
            </p>

            <p>
              Please read this Privacy Policy carefully. By using and accessing
              any of the Services, you agree to the collection, use, and
              disclosure of your information as described in this Privacy
              Policy. If you do not agree to this Privacy Policy, please do not
              use or access any of the Services.
            </p>

            <Heading my={5}>Changes to This Privacy Policy </Heading>

            <p>
              We may update this Privacy Policy from time to time, including to
              reflect changes to our practices or for other operational, legal,
              or regulatory reasons. We will post the revised Privacy Policy on
              the Site, update the &quot;Last updated&quot; date and take any
              other steps required by applicable law.
            </p>

            <Heading my={5}>
              How We Collect and Use Your Personal Information
            </Heading>

            <p>
              To provide the Services, we collect and have collected over the
              past 12 months personal information about you from a variety of
              sources, as set out below. The information that we collect and use
              varies depending on how you interact with us.
            </p>

            <p>
              In addition to the specific uses set out below, we may use
              information we collect about you to communicate with you, provide
              the Services, comply with any applicable legal obligations,
              enforce any applicable terms of service, and to protect or defend
              the Services, our rights, and the rights of our users or others.
            </p>

            <Heading my={5}>What Personal Information We Collect</Heading>

            <p>
              The types of personal information we obtain about you depends on
              how you interact with our App and use our Services. When we use
              the term &quot;personal information&quot;, we are referring to
              information that identifies, relates to, describes or can be
              associated with you. The following sections describe the
              categories and specific types of personal information we collect.
            </p>

            <Heading my={5}>Information We Collect Directly from You</Heading>

            <p>
              Information that you directly submit to us through our Services
              may include:
            </p>

            <p>
              - Basic contact details including your name, message, id, etc.
            </p>

            <p>
              Some features of the Services may require you to directly provide
              us with certain information about yourself. You may elect not to
              provide this information, but doing so may prevent you from using
              or accessing these features.
            </p>

            <Heading my={5}>Information We Collect through Cookies</Heading>

            <p>
              We also automatically collect certain information about your
              interaction with the Services (&quot;Usage Data&quot;). To do
              this, we may use cookies, pixels and similar technologies
              (&quot;Cookies&quot;). Usage Data may include information about
              how you access and use our Site and your account, including device
              information, browser information, information about your network
              connection, your IP address and other information regarding your
              interaction with the Services.
            </p>

            <Heading my={5}>Information We Obtain from Third Parties</Heading>

            <p>
              Finally, we may obtain information about you from third parties,
              including from vendors and service providers who may collect
              information on our behalf, such as:
            </p>

            <p>
              Any information we obtain from third parties will be treated in
              accordance with this Privacy Policy. We are not responsible or
              liable for the accuracy of the information provided to us by third
              parties and are not responsible for any third party's policies or
              practices. For more information, see the section below, Third
              Party Websites and Links.
            </p>

            <Heading my={5}>How We Use Your Personal Information</Heading>

            <p>
              At our App, we value your privacy and are committed to protecting
              your personal information. As we do not have a login or
              registration system, we do not collect personally identifiable
              information (PII) such as your name, email address, or contact
              details.
            </p>

            <p>
              However, we do collect certain non-personal information through
              Hotjar and Google Analytics to improve your experience on our
              website. Here's how we use the information we gather:
            </p>

            <p>
              Listening Data: We track the music you listen to, including the
              duration and frequency of your sessions. This helps us understand
              your preferences and interests, enabling us to provide you with a
              more personalized and enjoyable listening experience.
            </p>

            <p>
              Geolocation: We collect general location information, such as your
              country or region, to better understand our audience and tailor
              our content accordingly. This data allows us to offer
              region-specific radio stations or music recommendations that may
              align with your interests.
            </p>

            <p>
              Usage Analytics: We utilize tools like Hotjar and Google Analytics
              to gather aggregated data on website usage patterns, such as the
              number of visits, page views, and interaction metrics. These
              insights help us analyze and optimize our website's performance,
              identify any technical issues, and enhance its functionality for
              all users.
            </p>

            <p>
              Cookies and Similar Technologies: We may use cookies or similar
              technologies to collect and store certain information about your
              browsing behavior on our website. This data assists us in
              improving site navigation, remembering your preferences, and
              providing relevant content.
            </p>

            <p>
              Data Security: We take appropriate measures to safeguard the data
              we collect, ensuring it is protected against unauthorized access,
              loss, or alteration. We adhere to industry-standard security
              protocols to maintain the confidentiality and integrity of your
              information.
            </p>

            <p>
              Third-Party Access: We do not share your personal information with
              third parties for marketing or advertising purposes. However, we
              may share aggregated and anonymized data with trusted partners or
              service providers to further improve our website's functionality
              and user experience.
            </p>

            <p>
              Please note that while we strive to protect your personal
              information, no method of data transmission over the internet or
              electronic storage is entirely secure. We encourage you to review
              our Privacy Policy for more detailed information on how we handle
              your data and your rights regarding its collection and usage.
            </p>

            <p>
              If you have any concerns or questions about the privacy of your
              information or our data practices, please don't hesitate to
              contact us.
            </p>

            <Heading my={5}>How We Disclose Personal Information</Heading>

            <p>
              In certain circumstances, we may disclose your personal
              information to third parties for legitimate purposes subject to
              this Privacy Policy. Such circumstances may include:
            </p>

            <p>
              - With vendors or other third parties who perform services on our
              behalf (e.g., IT management, data analytics, customer support and
              cloud storage. - When you direct, request us or otherwise consent
              to our disclosure of certain information to third parties, such as
              to ship you products or through your use of social media widgets
              or login integrations, with your consent. - With our affiliates or
              otherwise within our corporate group, in our legitimate interests
              to run a successful business. - In connection with a business
              transaction such as a merger or bankruptcy, to comply with any
              applicable legal obligations (including to respond to subpoenas,
              search warrants and similar requests), to enforce any applicable
              terms of service, and to protect or defend the Services, our
              rights, and the rights of our users or others.
            </p>

            <p>
              We have, in the past 12 months disclosed the following categories
              of personal information and sensitive personal information
              (denoted by *) about users for the purposes set out above in
              &quot;How we Collect and Use your Personal Information&quot; and
              &quot;How we Disclose Personal Information&quot;:
            </p>

            <Heading my={5}>User Generated Content</Heading>

            <p>
              The Services may enable you to post product reviews and other
              user-generated content. If you choose to submit user generated
              content to any public area of the Services, this content will be
              public and accessible by anyone.
            </p>

            <p>
              We do not control who will have access to the information that you
              choose to make available to others, and cannot ensure that parties
              who have access to such information will respect your privacy or
              keep it secure. We are not responsible for the privacy or security
              of any information that you make publicly available, or for the
              accuracy, use or misuse of any information that you disclose or
              receive from third parties.
            </p>

            <Heading my={5}>Third-Party Websites and Links</Heading>

            <p>
              Our App may provide links to websites or other online platforms
              operated by third parties. If you follow links to sites not
              affiliated or controlled by us, you should review their privacy
              and security policies and other terms and conditions. We do not
              guarantee and are not responsible for the privacy or security of
              such sites, including the accuracy, completeness, or reliability
              of information found on these sites. Information you provide on
              public or semi-public venues, including information you share on
              third-party social networking platforms may also be viewable by
              other users of the Services and/or users of those third-party
              platforms without limitation as to its use by us or by a third
              party. Our inclusion of such links does not, by itself, imply any
              endorsement of the content on such platforms or of their owners or
              operators, except as disclosed on the Services.
            </p>

            <Heading my={5}>Children's Data</Heading>

            <p>
              The Services are not intended to be used by children, and we do
              not knowingly collect any personal information about children. If
              you are the parent or guardian of a child who has provided us with
              their personal information, you may contact us using the contact
              details set out below to request that it be deleted.
            </p>

            <p>
              As of the Effective Date of this Privacy Policy, we do not have
              actual knowledge that we &quot;share&quot; or &quot;sell&quot; (as
              those terms are defined in applicable law) personal information of
              individuals under 16 years of age.
            </p>

            <Heading my={5}>Security and Retention of Your Information</Heading>

            <p>
              Please be aware that no security measures are perfect or
              impenetrable, and we cannot guarantee &quot;perfect
              security.&quot; In addition, any information you send to us may
              not be secure while in transit. We recommend that you do not use
              unsecure channels to communicate sensitive or confidential
              information to us.
            </p>

            <p>
              How long we retain your personal information depends on different
              factors, such as whether we need the information to maintain your
              account, to provide the Services, comply with legal obligations,
              resolve disputes or enforce other applicable contracts and
              policies.
            </p>

            <Heading my={5}>Your Rights and Choices</Heading>

            <p>
              Depending on where you live, you may have some or all of the
              rights listed below in relation to your personal information.
              However, these rights are not absolute, may apply only in certain
              circumstances and, in certain cases, we may decline your request
              as permitted by law.
            </p>

            <p>
              - Right to Access / Know. You may have a right to request access
              to personal information that we hold about you, including details
              relating to the ways in which we use and share your information. -
              Right to Delete. You may have a right to request that we delete
              personal information we maintain about you. - Right to Correct.
              You may have a right to request that we correct inaccurate
              personal information we maintain about you. - Right of
              Portability. You may have a right to receive a copy of the
              personal information we hold about you and to request that we
              transfer it to a third party, in certain circumstances and with
              certain exceptions.
            </p>

            <p>
              - Right to Opt out of Sale or Sharing or Targeted Advertising. You
              may have a right to direct us not to &quot;sell&quot; or
              &quot;share&quot; your personal information or to opt out of the
              processing of your personal information for purposes considered to
              be &quot;targeted advertising&quot;, as defined in applicable
              privacy laws. Please note that if you visit our App with the
              Global Privacy Control opt-out preference signal enabled,
              depending on where you are, we will automatically treat this as a
              request to opt-out of the &quot;sale&quot; or &quot;sharing&quot;
              of information for the device and browser that you use to visit
              the App.
            </p>

            <p>
              You may exercise any of these rights where indicated on our App or
              by contacting us using the contact details provided below.
            </p>

            <Heading my={5}>Complaints</Heading>

            <p>
              If you have complaints about how we process your personal
              information, please contact us using the contact details provided
              below. If you are not satisfied with our response to your
              complaint, depending on where you live you may have the right to
              appeal our decision by contacting us using the contact details set
              out below, or lodge your complaint with your local data protection
              authority.
            </p>

            <Heading my={5}>International Users</Heading>

            <p>
              Please note that we may transfer, store and process your personal
              information outside the country you live in, including the United
              States. Your personal information is also processed by staff and
              third party service providers and partners in these countries. If
              we transfer your personal information out of Europe, we will rely
              on recognized transfer mechanisms like the European Commission's
              Standard Contractual Clauses, or any equivalent contracts issued
              by the relevant competent authority of the UK, as relevant, unless
              the data transfer is to a country that has been determined to
              provide an adequate level of protection.
            </p>

            <Heading my={5}>Contact</Heading>

            <p>
              Should you have any questions about our privacy practices or this
              Privacy Policy, or if you would like to exercise any of the rights
              available to you, please email us at{' '}
              <b>contact@radio-crestin.com</b>.
            </p>
          </Box>
          <Footer />
          <Box mb={{base: 40, lg: 20}} />
        </Container>
      </Body>
      <Analytics />
    </>
  );
}
